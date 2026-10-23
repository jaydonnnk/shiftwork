# Slice 43 implementation plan, 2026-10-23

Authority: the user's go-ahead "Yes, start S43 on shiftwork/slice-43." under the approved Gate 4 S43 entry and the approved Gate 2/3 S43/S46 backtrack and offline-mode clarification.
Branch: `shiftwork/slice-43`, cut from main `1f25107`.
No live call, install, deployment, commit or push is authorized by this plan.

## Findings from mapping the code

- The gateway (`shiftwork/gateway/service_inference.py`) returns only `{"selected_tool": ...}` and raises `MODEL_TOOL_NOT_ALLOWED` on any other content.
- The trusted driver (`DRIVER_SOURCE` in `shiftwork/executor/tokenfactory.py`) forwards only `selected_tool`, and implements exactly two tools: `public_record_lookup` (by `entity_ref` and `record_kind`) and `public_catalog_search` (by `genre`).
- The mission is bound per pack, not per shift: `EngagementPack.mission_path` is read at eight or more call sites in `shiftwork/orchestrator.py` (lines 129, 382, 569, 859, 1717, 2610 and others), and line 382 checks `context.requirement_set_hash` against the current pack mission bytes.
- Bellwether pins live in `shiftwork/packs/registry.py` `_BELLWETHER_PINS`; the starter path lives in `config.PIVOT_STARTER_ARTIFACT_PATHS`.
- `LocalProcessAdapter` refuses any inference grant (`shiftwork/executor/local_process.py:133`).

## Design decisions

1. **Two gateway modes, chosen by policy.**
`InferencePolicy` gains `task_vocabulary: tuple[str, ...] = ()`.
Empty keeps the existing tool-name mode byte-for-byte, so every historical fixture and run keeps working.
Non-empty selects plan mode (Gate 3 section 3.5).
2. **Plan mode is strict.**
Content (after surrounding whitespace) must be a JSON object `{"plan": [{"task_type": str, "tool_name": str}, ...]}` with at least one step and no other keys.
Checks run in order: schema, then task type, then tool.
Failures return `plan: null` plus one of `SCHEMA_INVALID`, `TASK_TYPE_UNKNOWN`, `TOOL_NOT_ALLOWED`.
Markdown code fences are a schema failure, not something the gateway strips: that is a repair the learner can make in the prompt.
A plan failure is not a `GatewayRejected`; the call counts and the run continues.
3. **Driver passthrough.**
In plan mode the driver replies `{"plan": ..., "plan_failure": ...}` to the service.
`/tool` still refuses any unlisted tool.
4. **Enlarged tool vocabulary.**
Mission v2 adds `public_price_lookup`, `public_stock_lookup` and `public_availability_lookup`, each a fixed-kind view over the same public records as `public_record_lookup`.
That gives five tools and makes the per-task tool choice meaningful without new data.
5. **Per-shift mission resolution (largest change).**
`EngagementPack` gains an ordered tuple of mission versions.
A shift's mission is resolved from its captured context's `requirement_set_hash`, never from current executor config, so a restart with different credentials never changes an open shift.
A new Bellwether shift binds v2 only when the app's configured executor is `tokenfactory`; otherwise v1.
Every `pack.mission_path` call site moves to a shift-aware resolver.
6. **Offline demo harness.**
`demos/s43_task_plan.py` runs the new starter as a subprocess against a local test gateway that serves labelled operator-authored test replies.
It is test infrastructure, never a product executor, and its output says "test reply" on every line.

## Work order

| Step | Change | Proof |
|---|---|---|
| 1 | Protocol and gateway plan mode; driver passthrough; adapter forwards `task_vocabulary` | Obligations 61 and 63 (gateway arms) with one mutation per guard |
| 2 | Mission v2 draft and five-tool driver support | Mission loads; driver tool tests |
| 3 | Per-shift mission resolver and executor-gated binding | Binding test: `tokenfactory` binds v2, `recorded` binds v1, a swap mutation fails; existing suites unchanged |
| 4 | New starter with no rescue code | Obligation 62 offline arm with the re-added-guard mutation |
| 5 | Demo, full offline suite, `00-status.md` record, cleanup scan | Known baseline: 1454 passed, 1 failed (`port_dead`), 1 skipped |

Operator review of mission v2 and the starter bytes, and their pins in `_BELLWETHER_PINS`, happen after step 4 and before acceptance.

## Progress

- [x] Step 1 (2026-10-23): plan mode in `shiftwork/gateway/protocol.py` and `service_inference.py` (`parse_task_plan`, `_plan_reply`), driver passthrough and adapter `task_vocabulary` in `shiftwork/executor/tokenfactory.py`.
  Tests: `tests/executor/test_task_plan_gateway.py` (14 cases, obligation 61 and the gateway arms of 63).
  Mutations: `tests/s43_mutation_proofs.py`, 10 of 10 killed, each restored byte-identically; receipt `docs/plans/shiftwork/evidence/slice43-step1-mutations-2026-10-23.txt`.
  Full offline suite: 1 failed (`port_dead`, known), 1468 passed, 1 skipped.
  No live call. Obligation 63 still needs its mission-derivation arm in step 3 (adapter fed from mission v2, never from the request).
- [x] Step 2 (2026-10-23): mission v2 draft, `MissionSpec.task_vocabulary`, three fixed-kind driver tools.
- [x] Step 3 (2026-10-23): `shift_mission_bindings`, `EngagementPack.mission_versions`, `orchestrator.shift_mission_path` and `bind_new_shift_mission` (inheritance chosen by the user), `orchestrator.service_adapter` for all three adapter sites.
  The resolver returns a path; each caller keeps its own read so existing TOCTOU and hash checks still apply.
- [x] Step 4 (2026-10-23): `task_plan_starter_service.py`, obligation 62 tests with the re-added-guard mutation.
- [x] Step 5 (2026-10-23): `demos/s43_task_plan.py`, 27 of 27 mutations killed, full suite as recorded in `00-status.md`.
- [x] Operator review and pins for mission v2 and the starter (user, 2026-10-24).
