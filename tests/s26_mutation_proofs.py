"""Named S26 mutations for the curation guards (obligation 48).

Every row faults one guard of ``shiftwork/curation/`` and must fail its named test
at an assertion, never as a crash, a timeout or a syntax error. The anchors are
single-occurrence literal statements, each independently breakable; each target
file is restored byte-for-byte afterwards and the restore is digest-checked.

The rows cover, one at a time: each ablation threshold branch (useful structural
count, domain spread, reviewed-candidate cap, median review time, unverified or
non-allow-listed effects, the executable-change rule), the earliest qualifying
publication-time selection, the polling membership rule, the hash-change
detection, the window and threshold retention checks, the freeze digest
immutability check, the results-before-freeze freeze refusal, the
results-before-freeze comparator refusal, the structural-event-outside-the-
watch-list refusal, and each runtime import probe (the app probe catches an
injected curation import; the curation probe catches an injected sealed-store
import).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = "shiftwork/curation/pipeline.py"
ABL = "shiftwork/curation/ablation.py"

FEWER = "tests/curation/test_ablation.py::test_ablation_drops_when_fewer_than_two_useful_structural_discoveries"
DOMAINS = "tests/curation/test_ablation.py::test_ablation_drops_when_useful_structural_discoveries_span_one_domain"
CAP = "tests/curation/test_ablation.py::test_ablation_drops_when_a_useful_fixture_exceeds_ten_reviewed_candidates"
MEDIAN = "tests/curation/test_ablation.py::test_ablation_drops_when_median_review_time_exceeds_thirty_minutes"
EFFECTS = "tests/curation/test_ablation.py::test_ablation_drops_on_any_unverified_or_non_allow_listed_effect"
RULE = "tests/curation/test_ablation.py::test_ablation_drops_when_discoveries_are_link_or_prose_only"
EARLIEST = "tests/curation/test_ablation.py::test_earliest_qualifying_publication_time_dedupes_and_excludes"
POLLING = "tests/curation/test_ablation.py::test_polling_keeps_known_urls_and_never_sees_structural_events"
MATRIX = "tests/curation/test_ablation.py::test_freeze_retention_matrix"
IMMUTABLE = "tests/curation/test_ablation.py::test_freeze_immutability_digest_and_reefuse"
PRE_RESULTS = "tests/curation/test_ablation.py::test_freeze_refuses_unverified_corpus_and_pre_results"
REFUSALS = "tests/curation/test_ablation.py::test_refusals_for_ordering_dangling_references_and_missing_reviews"
PROBES = "tests/curation/test_ablation.py::test_import_probes_load_no_forbidden_modules"

CASES = (
    ("useful_count_threshold_ignored", ABL,
     "            passed=len(useful) >= thresholds.min_structural_discoveries,\n",
     "            passed=len(useful) >= 0,\n",
     FEWER, 1, None),
    ("domain_spread_threshold_ignored", ABL,
     "            passed=len({row.domain for row in useful}) >= thresholds.min_structural_domains,\n",
     "            passed=len({row.domain for row in useful}) >= 0,\n",
     DOMAINS, 1, None),
    ("reviewed_candidate_cap_ignored", ABL,
     "        if len(change.candidates) > thresholds.max_reviewed_candidates_per_useful_fixture\n",
     "        if len(change.candidates) > 10**9\n",
     CAP, 1, None),
    ("median_review_threshold_ignored", ABL,
     "            passed=median <= thresholds.max_median_review_minutes,\n",
     "            passed=True,\n",
     MEDIAN, 1, None),
    ("unverified_effects_threshold_ignored", ABL,
     "            passed=len(violations) <= thresholds.max_unverified_content_effects,\n",
     "            passed=True,\n",
     EFFECTS, 1, None),
    ("executable_change_rule_ignored", ABL,
     "    rule_holds = not found_structural or executable_found > 0\n",
     "    rule_holds = True\n",
     RULE, 1, None),
    ("earliest_selection_reversed", ABL,
     "                earliest_qualifying=min((published for _, published in qualifying), default=None),\n",
     "                earliest_qualifying=max((published for _, published in qualifying), default=None),\n",
     EARLIEST, 1, None),
    ("polling_membership_forced_visible", ABL,
     "                polling_visible=normalize_url(event.source_url) in watched,\n",
     "                polling_visible=True,\n",
     POLLING, 1, None),
    ("polling_hash_change_detection_weakened", ABL,
     "        sorted(url for url, baseline in known_urls.items() if url in fetched and fetched[url] != baseline)\n",
     "        sorted(url for url, baseline in known_urls.items() if url in fetched)\n",
     POLLING, 1, None),
    ("window_retention_check_removed", PIPE,
     "    if (preregistration.window.start, preregistration.window.end) != (WINDOW_START, WINDOW_END):\n",
     "    if False:\n",
     MATRIX, 1, None),
    ("threshold_retention_check_removed", PIPE,
     "    if preregistration.thresholds != pinned:\n",
     "    if False:\n",
     MATRIX, 1, None),
    ("freeze_digest_check_removed", PIPE,
     "        if current != self.freeze.preregistered_digest:\n",
     "        if False:\n",
     IMMUTABLE, 1, None),
    ("freeze_before_results_check_removed", PIPE,
     "        if (\n"
     "            self.outcomes.discovery_runs\n"
     "            or self.outcomes.sources\n"
     "            or self.outcomes.reviews\n"
     "            or self.outcomes.frozen_changes\n"
     "        ):\n",
     "        if False:\n",
     PRE_RESULTS, 1, "freeze_preregistration"),
    ("results_before_freeze_refusal_removed", ABL,
     "        if run.started_at < freeze.frozen_at:\n",
     "        if False:\n",
     REFUSALS, 1, None),
    ("structural_event_in_watch_list_refusal_removed", ABL,
     '        if event.kind == "structural" and in_list:\n',
     "        if False:\n",
     REFUSALS, 1, None),
    # The two subprocess probes must themselves be failing-capable: each injection
    # targets exactly the edge that probe owns.
    ("app_probe_curation_import_injected", "shiftwork/app.py",
     "from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget\n",
     "from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget\n"
     "from shiftwork.curation import pipeline as _s26_probe_import\n",
     PROBES, 1, None),
    ("curation_probe_sealed_import_injected", PIPE,
     "from shiftwork.domain.models import Id, JsonValue\n",
     "from shiftwork.domain.models import Id, JsonValue\n"
     "from shiftwork.sealed import store as _s26_probe_import\n",
     PROBES, 1, None),
)

EXPECTED_ASSERTIONS = {
    "useful_count_threshold_ignored": "assert (not True)",
    "domain_spread_threshold_ignored": "assert (not True)",
    "reviewed_candidate_cap_ignored": "assert not True",
    "median_review_threshold_ignored": "assert (not True)",
    "unverified_effects_threshold_ignored": "assert (not True)",
    "executable_change_rule_ignored": "assert (not True)",
    "earliest_selection_reversed": "2026, 4, 18",
    "polling_membership_forced_visible": "and not True",
    "polling_hash_change_detection_weakened": "a.example/one",
    "window_retention_check_removed": "DID NOT RAISE",
    "threshold_retention_check_removed": "DID NOT RAISE",
    "freeze_digest_check_removed": "DID NOT RAISE",
    "freeze_before_results_check_removed": "DID NOT RAISE",
    "results_before_freeze_refusal_removed": "DID NOT RAISE",
    "structural_event_in_watch_list_refusal_removed": "DID NOT RAISE",
    "app_probe_curation_import_injected": "shiftwork.curation",
    "curation_probe_sealed_import_injected": "shiftwork.sealed",
}


def _scoped(source: str, needle: str, replacement: str, scope: str | None) -> tuple[str, int]:
    """Apply one replacement, optionally restricted to one function's body."""
    if scope is None:
        return source.replace(needle, replacement), source.count(needle)
    head, tail = source.split(f"def {scope}(", 1)
    body, rest = tail.split("\ndef ", 1)
    return (head + f"def {scope}(" + body.replace(needle, replacement) + "\ndef " + rest,
            body.count(needle))


def main() -> int:
    wanted = {argument for argument in sys.argv[1:] if not argument.startswith("-")}
    rows = [case for case in CASES if not wanted or case[0] in wanted]
    failures = []
    for name, relative, needle, replacement, test, expected_count, scope in rows:
        path = ROOT / relative
        original = path.read_bytes()
        source = original.decode("utf-8").replace("\r\n", "\n")
        mutated, count = _scoped(source, needle, replacement, scope)
        if count != expected_count:
            print(f"SKIP {name}: anchor count {count}, expected {expected_count}", flush=True)
            failures.append(name)
            continue
        try:
            path.write_bytes(mutated.encode("utf-8"))
            command = [sys.executable, "-m", "pytest", test, "-q", "--tb=short"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=300, check=False)
        finally:
            path.write_bytes(original)
        if path.read_bytes() != original:
            print(f"RESTORE_MISMATCH {name}: {relative} was not restored byte-for-byte", flush=True)
            failures.append(name)
            continue
        assertion_lines = [line.strip() for line in result.stdout.splitlines()
                           if line.startswith("E   ")]
        caught = (result.returncode == 1 and f"FAILED {test}" in result.stdout
                  and "ERROR " not in result.stdout and "SyntaxError" not in result.stdout
                  and EXPECTED_ASSERTIONS[name] in result.stdout
                  and any(line.startswith(("E   assert", "E   AssertionError", "E   Failed:"))
                          for line in assertion_lines))
        print(f"{'FAIL_CAUGHT' if caught else 'UNPROVEN'} {name}: {test.split('::')[-1]} "
              f"assertion={assertion_lines[:2]}", flush=True)
        if not caught:
            failures.append(name)
            print((result.stdout + result.stderr)[-2200:], flush=True)
    print(f"S26_MUTATIONS caught={len(rows) - len(failures)} total={len(rows)} "
          f"unproven={','.join(failures) or 'none'}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
