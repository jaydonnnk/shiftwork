# Slice 9 implementation plan

Date: 2026-09-21. Authority: approved `04-slices.md` S5 and the user's instruction to plan and start Slice 9. Branch: `shiftwork/slice-9`. Gates remain approved; no later slice is authorized by this work.

## Goal

Replace the tracer with the Bellwether operational room and real board/customer evidence, then pause for the user's visual judgment.

## Architecture and design

Keep the existing FastAPI process and plain HTML/CSS/JavaScript client. Author local SVG room artwork with HTML station controls; no framework, dependency, font download, external asset service or build step. The room stays visible beside a persistent evidence panel. Match the supplied fixed isometric composition, with warm wood, blue structural framing, a central learner-owned workbench, and a visibly locked evaluator.

Palette: navy structure `#202c40`, deep room `#172235`, parchment `#f5f3ed`, green workbench `#486c5b`, amber evidence `#edbd68`, red incident `#b34f45`. Use Georgia sparingly for the bookshop name, Segoe UI for controls and body, Consolas for exact evidence. One restrained evidence-path highlight, only for finalized data; reduced motion shows the final state immediately. GSAP guidance informs restraint, but adding the library is unnecessary and outside the dependency-free baseline.

## File responsibilities

- `shiftwork/client/index.html`: semantic shell, journey navigation, seven station controls, board/customer containers.
- `shiftwork/client/styles.css`: shared tokens, room/evidence layout, focus, responsive and reduced-motion states.
- `shiftwork/client/room.svg`: original decorative room artwork; no product values or essential labels baked into it.
- `shiftwork/client/app.js`: API loading, station/customer selection, exact evidence rendering and guarded lifecycle actions.
- `shiftwork/client/evidence.js`: pure run/output/check/event identity joins and byte decoding, exercised by Node's built-in test runner.
- `shiftwork/api/schemas.py`, `routes.py`, `shiftwork/orchestrator.py`: only the missing safe output projections needed by screen 03. Public comparison comes from the executed ordinal's public record in its own run snapshot, never sealed expectations.
- `tests/api/test_client_evidence.py`: real HTTP projection, byte/provenance/ordinal and absent-public-record tests.
- `tests/client/`: dependency-free rendered behavior checks where possible; browser checks remain required.
- `demos/client.py`: isolated local preview with a pinned Slice 8 trusted fixture, clearly labelled as fixture execution, not learner-authored execution.
- `00-status.md`: actual verification evidence and remaining limits, not invented success.

## Execution checklist

- [x] Baseline: `.venv/Scripts/python.exe -m pytest tests -q --ignore=tests/packaging`. No install; packaging test 51 excluded explicitly.
- [x] Write failing evidence projection tests, then implement structured customer answers and public comparison provenance. Keep arbitrary body bytes unchanged. No filesystem paths, future requests, sealed identities or expectations in new fields.
- [x] Write failing client checks, then implement the persistent room, board and customer panel. Join output/check/event by run plus ordinal/output identity, never array position. Render all linked results/events, not just the first.
- [x] Board shows committed contract/version, clearly labelled draft files, visible-check and change-log contents, unresolved incidents/limits, attempts and verified ledger totals. Do not infer decisions from saves/runs.
- [x] Customer view shows exact executed wording, controller-derived answer, downloadable/base64-preserved raw body, independently sourced public record with provenance, sealed reason codes and actual linked synthetic events.
- [x] Every business-state region keeps a visible `Synthetic scenario` label in loaded, empty, loading and error states. Clear stale selections/data on reload/failure. Failed/non-finalized runs never animate as successful.
- [x] Stations and top navigation work with keyboard and visible focus. Future authoring views explain their Slice 10/11 deferral without pretending to edit; evaluator is inspectable but never editable.
- [x] Start isolated preview and exercise real API-backed customer selection and refresh. Inspect 1280, 640 and 390 px, keyboard, reduced motion, no incidents, no run, loading and API failure; no horizontal page scrolling.
- [x] Prove rendered assertions fail when a synthetic label is removed and when evidence selection is misbound. Check console and network, run full authorized suite and `git diff --check`.
- [x] Check affected ADRs, record evidence, leave the actual URL for the user's design review. Do not begin Slice 10, commit or push.
- [x] Post-slice cleanup scan: not invoked in the implementation session (no architect-reviewer skill was available); the equivalent scan was performed in the 2026-09-21 independent verification round, and its findings were applied or reported (see the scan entry in `00-status.md`).

## Review round: 2026-09-21

The independent review of the preview returned REVISE with six material findings
(rendered-evidence harness blind spot; provenance recomputed from the mutable
snapshot path; missing comparison sources aborting raw retrieval; narrow station
reach; incident keyboard focus loss; desktop composition). All six were
adjudicated CONFIRMED and repaired with failing-capable proofs the same day; the
review's inherited evaluator-relevance limitation was recorded; no slice
currently owns relevance checking and the gap awaits the user's decision. Details,
commands and limits are in
`00-status.md` under "Slice 9 independent review round and repairs: 2026-09-21";
the user marked the merge to main (`4d5539a`, 2026-09-21) as the visual acceptance.

## Evidence limits

Local-process preview executes pinned trusted fixtures only. It does not establish hostile-code isolation, sandbox credentials, model integration, learning impact or full Test 1 PASS. A supplied composition reference does not mean pixel-identical production artwork; the rendered result remains subject to the user's design review.
