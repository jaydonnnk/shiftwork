# S23 Stonebridge exact-byte operator review packet

2026-10-07 Asia/Singapore. Branch `shiftwork/slice-23`; HEAD `3e02f1e`.
Status: READY FOR OPERATOR MATERIAL REVIEW, WITH DISCLOSED IGNORE-RULE EXCEPTION.
NOT APPROVED OR APPLIED. S23 remains incomplete.

Approval is limited to these 19 fictional material files, two proposed seals,
19 GTM material pins, three document bindings and three trusted-local fixture pins.
Application changes four production files: the manifest, protected family, registry
and configuration. All other material bytes stay exact. No live model, CRM,
customer message, credential, installation, spend, commit, push or S24/S25.

## Material decision

The starter incorrectly routes an APAC platform demo to the AMER owner. A uses
rules-first routing and conservative human review. B uses hand-authored synthetic
intent/confidence for direct routing. B has made no model call. Both plausible
decisions on the confident non-explicit buying signal are accepted; neither is ranked.

Suppressed accounts and companies below 50 employees are disqualified. Stale
enrichment (older than 3600000 ms), provider outage, unknown region/product,
ambiguous intent or confidence below 80 requires review. Current confident research
is disqualified. Explicit demo, pricing or security-review buying notes qualify.
Qualified owner follows the frozen six-entry region/product map; review uses
`revenue-review`. Disqualified signals create no owner, write or handoff.
Each first processed qualified or review signal has one synthetic owner and record. Review requires a
human-handoff record. Retries preserve the captured decision and produce no second
owner, record or handoff. Outputs do not establish any external CRM action.

Rules: [qualification and routing](../../../shiftwork/fixtures/documents/gtm/qualification_routing_rules.md).
Three public workloads each contain three requests. One unseen variant is reserved
per pair and shared by A/B; one comparison uses three of the six variants.

## Six protected expected decisions

This section is operator material. It must not enter learner responses or prompts.

| Variant | Condition | Decision | Owner and record | Handoff |
|---|---|---|---|---|
| 01 | APAC platform demo | QUALIFIED | owner-apac-platform; one record | None |
| 02 | EMEA analytics demo | QUALIFIED | owner-emea-analytics; one record | None |
| 03 | Ambiguous, confidence 35 | REVIEW | revenue-review; one record | One review record |
| 04 | Suppressed account | DISQUALIFIED | No owner or record | None |
| 05 | Stale enrichment | REVIEW | revenue-review; one record | One review record |
| 06 | Frozen existing-record retry | QUALIFIED | Retain existing APAC owner; no second write | None |

The `qualified_owner` field pins the qualified route only. In variants 03/05 the
actual review owner is `revenue-review`; in variant 04 there is no owner.

## Exact approval binding

Approval digest (SHA-256 of canonical inventory without this digest): `8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa`.
Machine packet: [current inventory](slice23-gtm-review-inventory.json).
The first-draft and pre-repair inventories/proposals are superseded. Their
bytes remain preserved in the original evidence and continuation preimages.

| Material path beneath shiftwork | Current SHA-256 | Proposed SHA-256 |
|---|---|---|
| fixtures/catalogs/gtm_v1.json | `a378f7ce2fd5b2506381eade910c4855424c9cf62676540c9ef932cca550f7b9` | `a378f7ce2fd5b2506381eade910c4855424c9cf62676540c9ef932cca550f7b9` |
| fixtures/mission/gtm_pipeline_v1.json | `de6e3794ccb3d1c4e5b0c29cff587ee0dad587bfc00f2751227dada2e02243ab` | `de6e3794ccb3d1c4e5b0c29cff587ee0dad587bfc00f2751227dada2e02243ab` |
| fixtures/state/gtm_pipeline_public_state.json | `614ebac546b7b26b5175db1b6963ecc0d4d26c901ad56a000ee8c60fda37a15f` | `614ebac546b7b26b5175db1b6963ecc0d4d26c901ad56a000ee8c60fda37a15f` |
| fixtures/state/gtm_compare_state_v1.json | `1a9d7cd051d691bcebed2917edc042ebc8f81dff6cf2b20b14f51c43bf9c834b` | `1a9d7cd051d691bcebed2917edc042ebc8f81dff6cf2b20b14f51c43bf9c834b` |
| fixtures/requests/gtm_pipeline_incident.jsonl | `77771e8a79224832208fd51d9cd513d38d5728edeab5a173c48408cda505badb` | `77771e8a79224832208fd51d9cd513d38d5728edeab5a173c48408cda505badb` |
| fixtures/requests/gtm_compare_manifest.json | `6b58826403dd11e37a4afefb0efc36a712a94c71e8207d80907a719eee1be4a9` | `e517f09bb92be0680324484850cc2a95611ac0034c973ce36f06d0ca2ce762bf` |
| fixtures/requests/gtm_compare_pair_01.jsonl | `7095b7a3ed2e0bd2bda8f8ab4594b7958adfdca420323d43235af101656d0497` | `7095b7a3ed2e0bd2bda8f8ab4594b7958adfdca420323d43235af101656d0497` |
| fixtures/requests/gtm_compare_pair_01_specs.json | `714433f66efb3308332df3fe130b19556fc7889365c88c809bd80f6abf87ef38` | `714433f66efb3308332df3fe130b19556fc7889365c88c809bd80f6abf87ef38` |
| fixtures/requests/gtm_compare_pair_02.jsonl | `47baa24e3446245f9fb861873e8953cc5f7058ef6914514a106d34054c282929` | `47baa24e3446245f9fb861873e8953cc5f7058ef6914514a106d34054c282929` |
| fixtures/requests/gtm_compare_pair_02_specs.json | `76019d7dea096438709d2a5f23bca202d86785e3907c59fd73a140677ae1e22c` | `76019d7dea096438709d2a5f23bca202d86785e3907c59fd73a140677ae1e22c` |
| fixtures/requests/gtm_compare_pair_03.jsonl | `a7d01171a95cf888c52dd6136a223c6f6b0322805543a89e2cae598b89e9625d` | `a7d01171a95cf888c52dd6136a223c6f6b0322805543a89e2cae598b89e9625d` |
| fixtures/requests/gtm_compare_pair_03_specs.json | `71b6ef3f82ae4f86d4836340e16596620a5c8f208e0aff739963900e93ea92f1` | `71b6ef3f82ae4f86d4836340e16596620a5c8f208e0aff739963900e93ea92f1` |
| sealed/cases/gtm_pipeline_ownership.json | `5c0b1aebe8e9c194084dc250148747c1e0df691d1881158e09694f3a3daba8d1` | `f3323eba764cc116df1439abe21ad094369936cd39b05641060d9bc646a9dd5f` |
| fixtures/artifacts/gtm/pipeline_starter_failure.py | `75be6938e5dbede87973a95f8ad56c3b099763475d4c98c72c8ccd929ae00a01` | `75be6938e5dbede87973a95f8ad56c3b099763475d4c98c72c8ccd929ae00a01` |
| fixtures/artifacts/gtm/gtm_compare_repair_a_workflow.py | `36a31ae4aca44d6adff0a10b5baf5b449a2f7ef52706eef192721f75f4964f23` | `36a31ae4aca44d6adff0a10b5baf5b449a2f7ef52706eef192721f75f4964f23` |
| fixtures/artifacts/gtm/gtm_compare_repair_b_workflow.py | `49cec35f5363a6bdcab60c66443fb193623063f9a404e3920aadbdc539d2ce9e` | `49cec35f5363a6bdcab60c66443fb193623063f9a404e3920aadbdc539d2ce9e` |
| fixtures/documents/gtm/revenue_team_brief.md | `71f72e619e08cb279339d70df19c583386e1e1ee3f310d4b19892ed15550ab66` | `71f72e619e08cb279339d70df19c583386e1e1ee3f310d4b19892ed15550ab66` |
| fixtures/documents/gtm/qualification_routing_rules.md | `d22940c6afa06aba4fdaafb9dc203bb42274c35d1b98381f7e88e1902af10046` | `d22940c6afa06aba4fdaafb9dc203bb42274c35d1b98381f7e88e1902af10046` |
| fixtures/documents/gtm/workflow_treatments.md | `6cb962ea773d0bf98eeab54c78d9ef93f3fa1dbc19a46db52e885c5c68027d29` | `6cb962ea773d0bf98eeab54c78d9ef93f3fa1dbc19a46db52e885c5c68027d29` |

Only the manifest/family bytes change: `review_status` becomes `OPERATOR_SEALED`
and the null seal becomes the exact canonical payload digest. Other draft metadata
stays byte-identical; review authority is the operator decision and literal pins.

Workloads canonical seal: `e0e3f5bddfa81e8a52dec188b79ca09dfd15b7d4c1ca819f08f2493ba0376454`.
Cases canonical seal: `e2bc5e303f7e9883e90fdba3d94bd6a6cdb2e0e0eaebe1d84eff4ba8590f1853`.
Catalog content hash (repository canonical format): `6a50acfd6a3731ddaf6e3c7e8a58fddda21e3676c815f3e300fdc2250bce7c2f`.

## Proposed source application

| File | Current SHA-256 | Proposed SHA-256 |
|---|---|---|
| shiftwork/packs/registry.py | `32b641dc66785719feac7ed26d5eca4baf542e9f14b5418b22fa4171c02672ec` | `e6cb4f3803479cf8aa35505a46463d83451b9a448c0fd96b162e2bae411c44d0` |
| shiftwork/config.py | `1fb59fea9668ab6cd2b008ee202f66daebe6da7ec3f34b45db743aed56321f08` | `ac8bb45fcbc186787da721b36aa6e30fc762f6d8cd899a07caf7c40c2ed009ff` |

Read-only proposed files: [application directory](evidence/slice23-lf-repair-2026-10-07/proposed-application/).
Source diffs: [registry](evidence/slice23-lf-repair-2026-10-07/registry-application.diff),
[config](evidence/slice23-lf-repair-2026-10-07/config-application.diff).

| Document ID | Station | Material path | SHA-256 |
|---|---|---|---|
| revenue-brief | Signal inbox | fixtures/documents/gtm/revenue_team_brief.md | `71f72e619e08cb279339d70df19c583386e1e1ee3f310d4b19892ed15550ab66` |
| qualification-rules | Workflow | fixtures/documents/gtm/qualification_routing_rules.md | `d22940c6afa06aba4fdaafb9dc203bb42274c35d1b98381f7e88e1902af10046` |
| workflow-treatments | Comparison bench | fixtures/documents/gtm/workflow_treatments.md | `6cb962ea773d0bf98eeab54c78d9ef93f3fa1dbc19a46db52e885c5c68027d29` |

| Offline fixture key | Artifact content hash | Files hash |
|---|---|---|
| gtm_starter | `4ee39e23810d0d58eed9eee1cdadb8c99010934da49ff581743e1564e9aecea2` | `a24b2e15a4ac11e41806e7f7a74e4cc35c3806bc722d40af5d38675bc9cdfea8` |
| gtm_compare_candidate_a | `80810dc77baccf00894634cf1d7b855346fc8e8bf05c1d983b621a0b7801eb33` | `aa363640af12212a57f8b74f2f698c9773d2693154c4972eaa599d9c603c456d` |
| gtm_compare_candidate_b | `ac90344963628ad964651f7877a64af9e35997ba7acb62e4636bca8d1087a10f` | `708ef678d36244d432455b0757feca0d4bd61a70eecc9493bf9a25419b91e7c2` |

Starter contract is bound in the inventory: catalog 1, 3000 ms limit,
NEVER_UNOWNED_OR_DUPLICATE_SIGNAL, REVIEW_AMBIGUOUS_SIGNAL and
DEDUPLICATE_PIPELINE_BY_SIGNAL. Exact declared limits disclose synthetic outputs.

## Verification and application boundary

Full offline suite: 1278 passed, 1 skipped, 2 warnings in 967.15s (0:16:07), exit 0. Packaging excluded.
Packet preimage/proposal verification: PASS. Original failed receipts remain.



The [offline checkpoint](slice23-lf-repair-checkpoint-2026-10-07.md) records focused,
source-omission, regression, architecture and byte-preservation receipts.
The disposable rehearsal proves mechanics only. It is not the reviewed S23 exit.

After explicit approval, recheck this entire inventory and all application preimages,
retain the exact user authorization, apply only the four proposed byte sequences and
verify the 19 pins, three document bindings and three fixture pins. Refuse any drift.
Then check actual admission/idempotent seeding, reproduce the reviewed starter and
run the six-slot trusted-local comparison with production pins. Record that comparison,
the unchanged comparison-time business rows and bounded assistance proof before
requesting S23 acceptance. S24 selection/operation and S25 live work remain separate.

## Incoming ignore-rule exception

The unexpected `/shiftwork/fixtures/requests/` ignore rule remains byte-exact
from the incoming handoff, with unverified ownership. The eight GTM request
drafts are explicitly included in this inventory despite being hidden from
ordinary status. This packet does not approve that rule or Git publication.
The old final-state preservation hold remains a historical failure; the
continuation reports its preservation checks with this exception explicit.

Post-approval verification includes transitioning prereview-only test assertions
and disposable helpers to strict approved-inventory checks, preserving all
refusal/fault guards and rerunning the full offline suite before acceptance.
The current suite is pre-application evidence; the review CLI remains draft-only.
