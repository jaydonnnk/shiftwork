# Slice 7 (2026-09-19/20): budget + rotation + incidents + repair

Goal: `04-slices.md` Slice 7. Branch `shiftwork/slice-7`. Committed in nine
batches, published and merged to main 2026-09-20 (`d4fe938`, pushed).

## Checklist

- [x] F1 prefix batch fixtures `bookshop_attempt_01..06.jsonl`
- [x] F2 repair transcripts `bookshop_repair_01_incident.json`, `bookshop_repair_02.json`, `bookshop_repair_03.json`
- [x] F3 sealed families 2/3: `bookshop_policy_exception.json`, `bookshop_hostile_instruction.json` (6 variants each, ordinals 1-6; sealed by the user 2026-09-20)
- [x] M1 domain: Run.request_batch_ref/shop_snapshot_ref; RotationDraw (+draw state)
- [x] M2 schema v4: runs columns + backfill, rotation_draws table, migration in one transaction
- [x] M3 repo: run columns, rotation_draws CRUD, incident resolution update, invalidate_rotation_group
- [x] M4 sealed/rotation.py: draw-without-replacement, variant refs, exhaustion, refill, retire/invalidate
- [x] M5 sealed/store.py: three families; load_drawn_cases(conn, run_id) = saved draws + open-incident regressions
- [x] M6 orchestrator: atomic start_run (budget + draws + batch + snapshot), execute_run uses run refs, finalize scores the run's snapshot + resolves incidents + INCIDENT_RESOLVED events
- [x] M7 routes: run outputs render against the run's snapshot
- [x] M8 app/config seeds: enabled families = the three real families; batch map
- [x] T tests: budget (24), atomicity + fault rollback (25), draws distinct/persisted/no-redraw (26), exhaustion + refill (27), repair resolution incl. same-version/failing-acceptance/failing-regression negatives (34), reservation-retention (9), future-stimuli absence (18), incident/draw reconstruction (23), retire/refill invalidation, shared_ordinal misconfiguration (incl. multi-ordinal), tiebreak, resolved-incident exclusion, sealed-store schema/ordinal validation; review-round additions: mixed-state invalidation filter, exposed-variant exclusion, genuine v3 upgrade
- [x] D demos: thin_path.py updated (3 families), repair_loop.py, all 6 demos pass
- [x] Mutation proofs: 20 mutations, each requiring an assertion-level failure in its named test (junit-based); 20/20 FAIL_CAUGHT, all sha256 restorations verified
- [x] MISTAKES.md: check-result-id double-count entry added
- [x] E evidence: 00-status Slice 7 section written 2026-09-20 (families 2/3 sealed by the user the same day)

## Verification results (2026-09-20, review-round repair)

```
pytest tests -q → 174 passed, 1 skipped, 2 warnings in 40.08s
pytest tests/orchestrator tests/api -q → 30 passed, 2 warnings in 3.44s
pytest tests/sealed -q → 43 passed, 2 warnings in 2.94s
mutation_proofs.py → 20/20 FAIL_CAUGHT at assertion level, all sha256_restored=True
harness self-check → vacuous / incidental / wrong-test / clean paths each classify correctly
```

Pre-repair numbers the same day (reproduced by the reviewer, now superseded): 170 passed + 1
skipped, 27 orchestrator+api, 15/15 with returncode-only detection (one row vacuous: the
invalidate state filter; catch was a sqlite3 binding-count crash).

Demos (all pass):
- thin_path: 3 CheckResults, 3 BACKLOG_RECORDED events, chain VALID
- repair_loop: 3 incidents opened, 3 resolved, 6 events, chain VALID
- lifecycle: 3 events, chain VALID
- finalize_run: 3 events, 3 incidents, idempotent re-finalize
- evaluate_transcript (passing): 6 pass / 0 fail, sockets blocked
- evaluate_transcript (failing): 0 pass / 6 fail, sockets blocked

Hash constants verified:
- batch 1: a16e1895f1f5d21a... ✓
- batch 6: 6055e2c82fe36544... ✓
- stale snapshot (content_hash of b64): 230d6f8aeb3eff61... ✓
- default snapshot (content_hash of b64): bd66a4136c8dc115... ✓
- thin-path artifact (catalog v1): 44abb79897239264... ✓

Migration v2→v4: verified by `test_existing_schema_two_gets_log_column_without_data_loss` and `test_existing_schema_three_gets_rotation_columns_without_data_loss` (adds log_ref, adds the run refs with the thin.jsonl / bookshop_snapshot.json backfill, creates rotation_draws); each migration branch mutated and caught at assertion level.

## Known limits

- The evaluate_transcript demo's socket blocking applies only to the scoring phase (asyncio on Windows needs socket internals during replay).
- Identity needle count is 4072 (not 4077 as the implementer claimed); 4 path needles with backslashes cannot match a serialized JSON surface directly (handled by path_forms).
- The select_variant tiebreak (`cases.index(case)`) is redundant with Python's `min` stability on the order-preserving filter for removal, but load-bearing for reversal (proved by mutation); the test is named for the behavior it guards (file-order tie preference), not for the term's necessity.

## Run log

- 2026-09-19: Slice 7 branch created; implementation landed (uncommitted).
- 2026-09-20: Adversarial verification and gap closing. Fixed 3 test bugs (monkeypatch.undo scope, family_cases read-after-overwrite, uncommitted UPDATE lock). Updated stale thin_path demo. Fixed evaluate_transcript for Slice 7 API. Added 8 new tests (repair negatives, future stimuli, incident reconstruction, tiebreak, shared_ordinal, resolved-incident exclusion, sealed-store validation). 15/15 mutation proofs green. MISTAKES.md entry added. Unused imports cleaned.
- 2026-09-20 (review round, adjudication REVISE): the invalidate-filter proof was vacuous (binding-count crash counted as caught; the corrected valid mutation passed the whole 27-test suite) and the harness could not tell a crash from an assertion. Repaired D1-D4: corrected mutation + mixed-state invalidation test; junit-based harness requiring the named expected test to fail at assertion level (proved against vacuous, incidental, wrong-test and clean mutations); wrong-exception shared_ordinal catches now AssertionError plus the previously untested multi-ordinal raise; unit proof for exposed-variant exclusion; genuine v3 upgrade test with v2/v3/backfill migration mutations; tiebreak test renamed to stop implying necessity. 20/20 clean; suites 174/30/43. Uncommitted; families 2/3 still await user sealing; no production file changed this round.
- 2026-09-20 (commit/publish/merge): nine focused commits `ab0819a..e23942b`; branch published; `--no-ff` merge `d4fe938` into main (lands the previously unmerged Slice 6 commits too); main pushed. Full suite on merged main: 174 passed, 1 skipped.
- 2026-09-20 (records): families 2/3 marked user-sealed; 00-status Slice 7 evidence section written; mirrors synced (AGENTS.md, SHIFTWORK_PLAN.md, store.py docstring) and all six demos plus the five hash constants re-verified. Uncommitted.
- 2026-09-20 (post-slice cleanup scan): no stale files found; all fixtures live (fault fixtures load through CASES and TRUSTED_LOCAL_FIXTURES f-strings); no dead symbols, no TODO/FIXME, no scratch outputs. One removal candidate: the empty `docs/plans/shiftwork/evidence/` directory. Awaiting user approval.
- 2026-09-20 (mirror-sync commit): AGENTS.md, SHIFTWORK_PLAN.md, 00-status.md and store.py docstring updated to reflect Slice 7 implemented/demonstrated status and families 2/3 sealed; committed to main.
