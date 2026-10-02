"""Test 17 (program design S6.D): the sealed import graph.

ADR 0001 fixes the read path: sealed case specs and expected values are
controller-side only, and no executor, assist, api or client module may import the
sealed store. Filesystem hiding is explicitly insufficient, so the boundary is
enforced structurally over the source tree rather than by convention.

Four arms, all failing-capable:

1. a static AST scan resolving every import (including relative imports) to a
   dotted name, so an indirect edge is caught;
2. an exact permitted-importer rule over the whole package, so a NEW importer
   anywhere fails, not just one inside the four named directories;
3. the named dynamic-import mechanisms (``__import__``, ``importlib.import_module``
   including import aliases, assignment aliases of either binding, the ``getattr``
   string form and ``exec``): literal targets are resolved and checked like plain
   imports, and computed targets are rejected outright rather than assumed safe.
   Arbitrary obfuscation is NOT covered: a runtime-computed attribute name, a
   string-built code object inside a literal or a separator-split path string
   evades this lint, and that residual is recorded in ``00-status.md`` rather than
   claimed here (the Gate 3 clause bounds the rule the same way);
4. a sealed-storage path rule: only ``config.py`` (which defines the constant) and
   ``sealed/store.py`` (the loader) may reference ``SEALED_CASES_DIR`` in any of
   the three named forms, so a controller module cannot read the sealed files by
   path while importing nothing.

Slice 14 adds ``shiftwork/assist/``. The scan includes it and an explicit
non-vacuity check requires the gateway source to enter the import graph.

Gate 3 wording note: test 17's spec says "only ``evaluator``" imports
``shiftwork.sealed``. The as-built and as-designed direction is the reverse:
``sealed/store.py`` is the controller-only loader and imports the evaluator's
``SealedCase`` types, while ``orchestrator.py`` calls the loader. Relocating the
loader into ``evaluator`` would give it file access and break test 11's purity
requirement, so this test enforces ADR 0001's forbidden set plus an exact
permitted-importer allowlist instead of the literal "only evaluator" clause.
"""

import ast
import re
from pathlib import Path

from shiftwork import config

REPO_ROOT = config.PACKAGE_DIR.parent
PACKAGE_ROOT = config.PACKAGE_DIR

SEALED_PACKAGE = "shiftwork.sealed"

# ADR 0001's forbidden readers, as package-relative directory names.
FORBIDDEN_DIRS = ("executor", "assist", "api", "client", "store", "ledger", "domain", "curation")

# The only modules permitted to import the sealed store: the controller lifecycle
# and the sealed package itself. Deliberately exact, so a new importer fails.
# Paths are package-relative to shiftwork/, matching _relative_path().
PERMITTED_IMPORTERS = frozenset({"orchestrator.py", "comparison_flow.py"})

# Catches plain literal references the AST import scan would miss; the dynamic-call
# analysis below covers the mechanisms a regex cannot see.
DYNAMIC_PATTERN = re.compile(r"shiftwork\.sealed|shiftwork\s+import\s+sealed")

# The configured sealed storage location. A controller module can read the sealed
# files through this attribute without importing anything, so it is guarded by name.
SEALED_PATH_ATTRIBUTE = "SEALED_CASES_DIR"

# The only files permitted to reference the storage location: the definition and the
# loader. Deliberately exact, so a new reader anywhere fails.
PERMITTED_PATH_READERS = frozenset({"config.py", "sealed/store.py"})


def _module_name(path: Path) -> str:
    return path.relative_to(REPO_ROOT).with_suffix("").as_posix().replace("/", ".")


def _relative_path(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def _package_files() -> list[Path]:
    files = sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    assert files, "no package modules found; the scan would be vacuous"
    return files


def _dotted_imports(tree: ast.AST, module_name: str) -> set[str]:
    """Every dotted name a module imports, resolving relative levels."""
    package_parts = module_name.split(".")[:-1]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - (node.level - 1)]
                prefix = ".".join([*base, node.module] if node.module else base)
            else:
                prefix = node.module or ""
            if prefix:
                names.add(prefix)
                names.update(f"{prefix}.{alias.name}" for alias in node.names)
            else:
                names.update(alias.name for alias in node.names)
    return names


def _imports_sealed(dotted: set[str]) -> bool:
    return any(name == SEALED_PACKAGE or name.startswith(f"{SEALED_PACKAGE}.") for name in dotted)


def _is_getattr_import_module(node: ast.expr, importlib_names: set[str]) -> bool:
    """True for ``getattr(<importlib alias>, "import_module")``, the string form of the attribute."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id in importlib_names
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "import_module"
    )


def _importlib_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Names bound to the ``importlib`` module and to ``importlib.import_module``.

    Import aliases (``import importlib as il``, ``from importlib import
    import_module as im``) are collected first, then assignment aliases
    (``mods = importlib``, ``fn = importlib.import_module``, ``fn2 = fn``), because
    a rebinding is the same object under a new name, not an unrelated one. The loop
    only ever adds names, so it terminates.
    """
    importlib_names = {"importlib"}
    import_module_names = {"import_module"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    import_module_names.add(alias.asname or alias.name)

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            bound_module = isinstance(value, ast.Name) and value.id in importlib_names
            bound_function = (
                (isinstance(value, ast.Name) and value.id in import_module_names)
                or (
                    isinstance(value, ast.Attribute)
                    and value.attr == "import_module"
                    and isinstance(value.value, ast.Name)
                    and value.value.id in importlib_names
                )
                or _is_getattr_import_module(value, importlib_names)
            )
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if bound_module and target.id not in importlib_names:
                    importlib_names.add(target.id)
                    changed = True
                if bound_function and target.id not in import_module_names:
                    import_module_names.add(target.id)
                    changed = True
    return importlib_names, import_module_names


def _dynamic_import_findings(tree: ast.AST) -> tuple[set[str], list[str]]:
    """Literal and computed targets for the named dynamic-import mechanisms.

    Covered call forms: ``__import__``, ``importlib.import_module`` (attribute or
    from-import, under an import alias or an assignment alias), the
    ``getattr(importlib, "import_module")`` string form, and ``exec`` (whose code
    object is never statically trustworthy, so every call is a computed target). A
    non-literal first argument cannot be resolved statically and is reported as a
    computed target, which the rule rejects rather than assumes safe. Arbitrary
    obfuscation is out of scope and stated so in the module docstring.
    """
    importlib_names, import_module_names = _importlib_bindings(tree)

    literal: set[str] = set()
    computed: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "exec":
            computed.append(f"line {node.lineno}: exec() is not a supported import mechanism")
            continue
        if isinstance(func, ast.Name) and func.id == "__import__":
            mechanism, target_args = "__import__", node.args
        elif isinstance(func, ast.Name) and func.id in import_module_names:
            mechanism, target_args = "importlib.import_module", node.args
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "import_module"
            and isinstance(func.value, ast.Name)
            and func.value.id in importlib_names
        ):
            mechanism, target_args = "importlib.import_module", node.args
        elif _is_getattr_import_module(func, importlib_names):
            mechanism, target_args = "importlib.import_module", node.args
        else:
            continue
        if not target_args:
            computed.append(f"line {node.lineno}: {mechanism} without a target argument")
            continue
        target = target_args[0]
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            literal.add(target.value)
        else:
            computed.append(f"line {node.lineno}: computed target for {mechanism}")
    return literal, computed


def _sealed_path_findings(tree: ast.AST) -> list[str]:
    """References to the configured sealed storage location, in the named forms.

    Covered: the ``SEALED_CASES_DIR`` attribute under any binding name (so a
    rebound module object does not hide it), a binding of the name, a direct import
    of the name, and a ``getattr(config, "SEALED_CASES_DIR")`` string lookup. Not
    covered: a runtime-computed attribute name or a separator-split path string,
    both recorded as residuals rather than claimed.
    """
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == SEALED_PATH_ATTRIBUTE:
            findings.append(f"line {node.lineno}: {SEALED_PATH_ATTRIBUTE} attribute reference")
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == SEALED_PATH_ATTRIBUTE
            for target in node.targets
        ):
            findings.append(f"line {node.lineno}: {SEALED_PATH_ATTRIBUTE} binding")
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == SEALED_PATH_ATTRIBUTE:
                    findings.append(f"line {node.lineno}: {SEALED_PATH_ATTRIBUTE} import")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == SEALED_PATH_ATTRIBUTE
        ):
            findings.append(f"line {node.lineno}: getattr string lookup of {SEALED_PATH_ATTRIBUTE}")
    return findings


def _path_reader_violations() -> dict[str, list[str]]:
    """Modules outside the permitted readers that reference the sealed storage path."""
    violations: dict[str, list[str]] = {}
    for path in _package_files():
        relative = _relative_path(path)
        if relative in PERMITTED_PATH_READERS:
            continue
        findings = _sealed_path_findings(ast.parse(path.read_text(encoding="utf-8")))
        if findings:
            violations[relative] = findings
    return violations


def _importers() -> tuple[dict[str, set[str]], list[str]]:
    """Importers of the sealed package plus every rejected computed target."""
    found: dict[str, set[str]] = {}
    computed: list[str] = []
    for path in _package_files():
        source = path.read_text(encoding="utf-8")
        module_name = _module_name(path)
        tree = ast.parse(source)
        dotted = _dotted_imports(tree, module_name)
        literal_dynamic, computed_targets = _dynamic_import_findings(tree)
        names = {name for name in dotted if name.startswith(SEALED_PACKAGE)}
        names |= {
            value
            for value in literal_dynamic
            if value == SEALED_PACKAGE or value.startswith(f"{SEALED_PACKAGE}.")
        }
        literal_reference = bool(DYNAMIC_PATTERN.search(source)) or bool(literal_dynamic)
        if names or literal_reference:
            found[_relative_path(path)] = names | (
                {"<dynamic string reference>"} if literal_reference else set()
            )
        computed.extend(
            f"{_relative_path(path)} {finding}" for finding in computed_targets
        )
    return found, computed


def _top_dir(relative: str) -> str | None:
    """The package-relative directory a module lives in, or None if top-level."""
    return relative.split("/")[0] if "/" in relative else None


def test_no_forbidden_module_imports_the_sealed_store() -> None:
    importers, computed = _importers()
    assert not computed, (
        "computed dynamic-import targets must be rejected for the named mechanisms, "
        "not assumed safe:\n" + "\n".join(computed)
    )
    violations = {
        relative: names
        for relative, names in importers.items()
        if _top_dir(relative) in FORBIDDEN_DIRS
    }
    assert not violations, f"ADR 0001 forbids these readers of {SEALED_PACKAGE}: {violations}"
    # Non-vacuity: the scan really did cover the forbidden directories.
    scanned_dirs = {_top_dir(_relative_path(path)) for path in _package_files()}
    for required in ("executor", "api"):
        assert required in scanned_dirs, f"{required}/ was never scanned"


def test_permitted_importers_are_exactly_the_controller() -> None:
    importers, _computed = _importers()
    inside_sealed = {
        relative for relative in importers if relative.startswith("sealed/")
    }
    outside_sealed = set(importers) - inside_sealed
    assert outside_sealed == PERMITTED_IMPORTERS, (
        f"expected exactly {sorted(PERMITTED_IMPORTERS)} to import {SEALED_PACKAGE}; "
        f"found {sorted(outside_sealed)}"
    )
    # Non-vacuity: the controller edge must actually exist, or the rule above
    # would pass against a package where nothing loads sealed cases at all.
    assert "orchestrator.py" in importers
    assert importers["orchestrator.py"], "orchestrator edge resolved to no dotted name"


def test_dynamic_import_scanner_rejects_each_named_mechanism() -> None:
    """Scanner self-test: every named mechanism's computed target is rejected.

    Safe forms are asserted alongside the rejected ones, so the rule cannot pass
    by flagging everything: a literal target resolves like a plain import, and the
    same literal behind an explicit alias resolves identically.
    """
    computed_cases = {
        "concatenated importlib target": (
            'import importlib\nimportlib.import_module("shiftwork." + "sealed")\n'
        ),
        "f-string importlib target": (
            'import importlib\nimportlib.import_module(f"shiftwork.{part}sealed")\n'
        ),
        "aliased importlib module": (
            "import importlib as il\nil.import_module(\"shiftwork.\" + NAME)\n"
        ),
        "aliased import_module function": (
            'from importlib import import_module as im\nim(pick_target())\n'
        ),
        "builtin __import__ concat": '__import__("shiftwork." + "sealed")\n',
        "assignment-aliased importlib module": (
            'import importlib\nmods = importlib\nmods.import_module("shiftwork." + "sealed")\n'
        ),
        "assignment-aliased import_module function": (
            'from importlib import import_module\nfn = import_module\nfn(pick_target())\n'
        ),
        "assignment alias of an alias": (
            'import importlib\nmods = importlib\nsecond = mods\nsecond.import_module(NAME)\n'
        ),
        "getattr importlib string form": (
            'import importlib\ngetattr(importlib, "import_module")("shiftwork." + "sealed")\n'
        ),
        "exec with a concatenated string": 'exec("import shiftwork." + "sealed")\n',
        "exec with a literal string": 'exec("import shiftwork.sealed")\n',
    }
    for label, source in computed_cases.items():
        _, computed = _dynamic_import_findings(ast.parse(source))
        assert computed, f"{label} was not rejected as a computed target"

    safe_cases = {
        "aliased function literal": (
            'from importlib import import_module as im\nim("shiftwork.sealed.store")\n'
        ),
        "assignment-aliased module literal": (
            'import importlib\nmods = importlib\nmods.import_module("shiftwork.sealed.store")\n'
        ),
        "getattr literal target": (
            'import importlib\ngetattr(importlib, "import_module")("shiftwork.sealed.store")\n'
        ),
    }
    for label, source in safe_cases.items():
        literal, computed = _dynamic_import_findings(ast.parse(source))
        assert literal == {"shiftwork.sealed.store"} and not computed, (
            f"{label} must resolve like a plain import, not be flagged"
        )
        assert _imports_sealed(literal), f"{label}: literal target must resolve to the sealed module"

    # Relative imports resolve to a dotted name (the forbidden-importer arm).
    dotted = _dotted_imports(ast.parse("from ..sealed import store\n"), "shiftwork.api.routes")
    assert "shiftwork.sealed.store" in dotted and _imports_sealed(dotted)


def test_only_the_loader_references_the_sealed_storage_path() -> None:
    """The boundary is a file-access rule, not only an import rule.

    A controller module can enumerate and read the sealed files by path without
    importing the sealed store, which the import scan cannot see. Every reference to
    the configured storage location is therefore located: only ``config.py`` (the
    definition) and ``sealed/store.py`` (the loader) may name it.

    Covered forms: the attribute under any binding name, a direct import of the name
    and a ``getattr`` string lookup. A runtime-computed attribute name or a
    separator-split path string is NOT covered; that residual is recorded.
    """
    violations = _path_reader_violations()
    assert not violations, (
        f"modules outside {sorted(PERMITTED_PATH_READERS)} reference "
        f"{SEALED_PATH_ATTRIBUTE}: {violations}"
    )
    # Non-vacuity: the detector really finds the references in the two permitted
    # files, so an empty violation set means "no reader", not "no detector".
    permitted = {
        relative: _sealed_path_findings(
            ast.parse((PACKAGE_ROOT / relative).read_text(encoding="utf-8"))
        )
        for relative in sorted(PERMITTED_PATH_READERS)
    }
    assert all(permitted.values()), f"the detector matched no real reference: {permitted}"

    cases = {
        "attribute form": "import shiftwork.config as cfg\ncfg.SEALED_CASES_DIR / 'family.json'\n",
        "rebound module form": "from shiftwork import config\nmods = config\nmods.SEALED_CASES_DIR\n",
        "binding form": "SEALED_CASES_DIR = PACKAGE_DIR / 'sealed' / 'cases'\n",
        "import form": "from shiftwork.config import SEALED_CASES_DIR\nSEALED_CASES_DIR\n",
        "getattr string form": 'from shiftwork import config\ngetattr(config, "SEALED_CASES_DIR")\n',
    }
    for label, source in cases.items():
        assert _sealed_path_findings(ast.parse(source)), f"{label} was not rejected"


def test_assist_gateway_is_scanned_for_forbidden_imports() -> None:
    """Test 17's assist arm now has real source and a failing-capable detector."""
    gateway_path = PACKAGE_ROOT / "assist" / "gateway.py"
    assert gateway_path in _package_files(), "assist gateway was absent from the package scan"
    importers, computed = _importers()
    assert "assist/gateway.py" not in importers
    assert not any(item.startswith("assist/") for item in computed)
    injected = ast.parse("from shiftwork.sealed import store\n")
    assert _imports_sealed(_dotted_imports(injected, "shiftwork.assist.gateway")), (
        "the import scanner must catch a sealed-store import injected into assist"
    )


def test_client_never_references_the_sealed_store() -> None:
    """The client is static HTML/CSS/JS, so it is scanned as text, not parsed."""
    client_dir = config.CLIENT_DIR
    assert client_dir.is_dir(), f"missing client directory: {client_dir}"
    files = sorted(path for path in client_dir.rglob("*") if path.is_file())
    assert files, "client directory is empty; the scan would be vacuous"
    leaks = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in ("shiftwork.sealed", "sealed/store", "sealed/cases", "expected_ref", "/api/sealed"):
            if needle in text:
                leaks.append(f"{path.relative_to(REPO_ROOT).as_posix()} references {needle!r}")
    assert not leaks, "\n".join(leaks)
