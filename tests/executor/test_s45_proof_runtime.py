"""A stale fault cache must not masquerade as restored source in a proof."""

import importlib.util
import os
from pathlib import Path
import py_compile
import runpy
import subprocess
import sys


def test_mutation_checks_import_restored_source_despite_a_poisoned_cache(tmp_path):
    module = tmp_path / "s45_cache_case.py"
    original = 'MODE = "forbid"\n'
    changed = original.replace("forbid", "ignore")
    module.write_text(original)
    stamp = module.stat().st_atime_ns, module.stat().st_mtime_ns
    module.write_text(changed)
    os.utime(module, ns=stamp)
    caches = {tmp_path / "__pycache__" / f"s45_cache_case.{sys.implementation.cache_tag}.pyc",
              Path(importlib.util.cache_from_source(str(module)))}
    for cache in caches:
        cache.parent.mkdir(parents=True, exist_ok=True)
        py_compile.compile(str(module), cfile=str(cache), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
    module.write_text(original)
    os.utime(module, ns=stamp)
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPYCACHEPREFIX"}
    stale = subprocess.run([sys.executable, "-c",
        f"import sys; sys.path.insert(0, {str(tmp_path)!r}); import s45_cache_case; print(s45_cache_case.MODE)"],
        env=env, capture_output=True, text=True, timeout=20)
    assert stale.returncode == 0 and stale.stdout.strip() == "ignore", "positive control must reproduce the cached fault"
    target = tmp_path / "test_s45_cache_control.py"
    target.write_text('import s45_cache_case\ndef test_source_is_restored():\n    assert s45_cache_case.MODE == "forbid"\n')
    run = runpy.run_path(str(Path(__file__).resolve().parents[1] / "s45_mutation_proofs.py"))["run"]
    result = run(str(target))
    assert result.returncode == 0, "mutation checks must read restored source, not cached faults"
