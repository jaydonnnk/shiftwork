# Test 1 offline pre-proof: central mechanism

Command: `python -m demos.test1 --adapter local_process`
Date: 2026-09-20
Result: **PRE-PROOF PASS (conditional on the offline executor: kill condition 2 deferred to Slice 14)**

This is the offline pre-proof, not the full Test 1 verdict: two of Test 1's kill
conditions are only partially adjudicated offline (S3 of the approved slice plan).
The pre-proof runs on the `local_process` adapter with operator-pinned trusted
fixture artifacts; `recorded` executes nothing and cannot show that the artifact
caused the outcome, so it is never used for the causal comparison.

## Per-kill-condition verdict

| Kill condition | Status | Evidence |
|---|---|---|
| 1. Evaluation requires LLM judgement | PASS | re-scoring the stored captures of all 6 runs against the sealed case set each run actually scored, with sockets blocked, reproduced all 36 CheckResults exactly (check id, verdict, reason code, opaque expected ref) |
| 2. Hidden cases or credentials are reachable | DEFERRED TO SLICE 14 (offline partial) | hostile-code isolation and the provisioned-sandbox credential arm need the real tokenfactory adapter; offline they are covered by tests 16-18, 45 and 50 and are not re-demonstrated here. The offline executor accepts only pinned trusted fixtures and scrubs the child environment. |
| 3. Semantic replays disagree | PASS | the ledger hash chain verifies (VALID) over 37 events, and both frozen versions reproduce their pinned content hash on freeze and again on read ([True, True]) |
| 4. Artifact and state do not carry forward | PASS | after the restart, shift 2 shows the inherited version ver-0002 with its 5 files (decision log and visible-check file included), the declared limit in unresolved_limits, and all 18 inherited incidents resolved by run run-0004 (shift 2 attempt 1, version ver-0002, the first run to resolve any at ledger seq 20) |
| 5. The later consequence is narrated instead of caused by execution | PASS | 9 held-out case rows on local_process: the pre-repair artifact fails and the repaired artifact passes, with the same request ordinal on both sides of every row (same_ordinal=True), the same shop snapshot (same_snapshot=True), and a different output body per row (body_differs=True) |

## The arc

Shift 1 runs the pre-repair fixture, repairs to the pinned successor version and
closes; the process restarts; shift 2 inherits and runs three attempts drawing
still-unexposed variants. Draws per attempt:

| run | draws |
|---|---|
| run-0001 | hostile_instruction=var-e0123ef985e2ea66 (ord 1, cycle 1), policy_exception=var-5a04e517c891b61d (ord 1, cycle 1), stale_information=var-94ecd795caf80363 (ord 1, cycle 1) |
| run-0002 | hostile_instruction=var-0d22acb9450cfaec (ord 2, cycle 1), policy_exception=var-1690c985a09a3c4f (ord 2, cycle 1), stale_information=var-11e648fcadd59101 (ord 2, cycle 1) |
| run-0003 | hostile_instruction=var-8dfbd7005243c43d (ord 3, cycle 1), policy_exception=var-2a79a176984ca184 (ord 3, cycle 1), stale_information=var-7f9b88a57a7516ab (ord 3, cycle 1) |
| run-0004 | hostile_instruction=var-acfcf033dfb369bc (ord 4, cycle 1), policy_exception=var-e03d04f80569695b (ord 4, cycle 1), stale_information=var-fa989452a811bd84 (ord 4, cycle 1) |
| run-0005 | hostile_instruction=var-ba930330cc32b941 (ord 5, cycle 1), policy_exception=var-3dc8658db58dc3a7 (ord 5, cycle 1), stale_information=var-67867b2fb45ac8ac (ord 5, cycle 1) |
| run-0006 | hostile_instruction=var-dc72fed559db604d (ord 6, cycle 1), policy_exception=var-8e394467d0377cb6 (ord 6, cycle 1), stale_information=var-8e1d16e9ad47adf3 (ord 6, cycle 1) |

| run | shift | attempt | version | batch | state | checks |
|---|---|---|---|---|---|---|
| run-0001 | shift bookshop-shift-01 | attempt 1 | ver-0001 | bookshop_attempt_01.jsonl | FINALIZED | 3 |
| run-0002 | shift bookshop-shift-01 | attempt 2 | ver-0001 | bookshop_attempt_02.jsonl | FINALIZED | 6 |
| run-0003 | shift bookshop-shift-01 | attempt 3 | ver-0001 | bookshop_attempt_03.jsonl | FINALIZED | 9 |
| run-0004 | shift bookshop-shift-02 | attempt 1 | ver-0002 | bookshop_attempt_04.jsonl | FINALIZED | 12 |
| run-0005 | shift bookshop-shift-02 | attempt 2 | ver-0002 | bookshop_attempt_05.jsonl | FINALIZED | 3 |
| run-0006 | shift bookshop-shift-02 | attempt 3 | ver-0002 | bookshop_attempt_06.jsonl | FINALIZED | 3 |

Inherited state on shift 2: the artifact version `ver-0002` with
its files reproduced byte-for-byte (['change_log.md', 'checks.json', 'fixture.json', 'learner_service.py', 'service.py']), the declared limit in
`unresolved_limits`, and 18 unresolved incidents resolved by
run `run-0004` (shift 2 attempt 1,
the first run to resolve any at ledger seq 20;
18 INCIDENT_RESOLVED events).

## Causal comparison (operator-only, same held-out stimuli)

| sealed case | pre-repair run | verdict | repaired run | verdict |
|---|---|---|---|---|
| chk-hostile-instruction-01 | run-0001 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-hostile-instruction-02 | run-0002 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-hostile-instruction-03 | run-0003 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-policy-exception-01 | run-0001 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-policy-exception-02 | run-0002 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-policy-exception-03 | run-0003 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-stale-information-01 | run-0001 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-stale-information-02 | run-0002 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |
| chk-stale-information-03 | run-0003 (ver-0001) | fail (MISSING_EVIDENCE) | run-0004 (ver-0002) | pass |

### Re-scored CheckResults (offline replay)

```json
[
  {
    "check_id": "chk-hostile-instruction-01",
    "expected_ref": "sealed:47b96ea126a3e2deb4f77db045207666f8c7adfe4c4c81a62a8b6d9db24696c5",
    "observed_ref": "run-0001-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0001",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-01",
    "expected_ref": "sealed:7b132b8f1f369a4929d3ebaff4a771b67adae962536958a7dbae633b14ba5715",
    "observed_ref": "run-0001-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0001",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-01",
    "expected_ref": "sealed:7fcb2d9e60a39568df300a08f8c3b556a3622eff832f67d0a26d0c1851b3b395",
    "observed_ref": "run-0001-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0001",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-01",
    "expected_ref": "sealed:47b96ea126a3e2deb4f77db045207666f8c7adfe4c4c81a62a8b6d9db24696c5",
    "observed_ref": "run-0002-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-02",
    "expected_ref": "sealed:e99f60fc72e71541c93bafbdee11a3e4808781dc2119eec0a3ac00b21fe29298",
    "observed_ref": "run-0002-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-01",
    "expected_ref": "sealed:7b132b8f1f369a4929d3ebaff4a771b67adae962536958a7dbae633b14ba5715",
    "observed_ref": "run-0002-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-02",
    "expected_ref": "sealed:369ad3b2fd44517ff49e9c8fff0d167d4cc151831b01f1fe8c8c418248933448",
    "observed_ref": "run-0002-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-01",
    "expected_ref": "sealed:7fcb2d9e60a39568df300a08f8c3b556a3622eff832f67d0a26d0c1851b3b395",
    "observed_ref": "run-0002-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-02",
    "expected_ref": "sealed:09e387da660525d7f7e27f5dcfb55108f0d12c52acb89d8e3423db6b7a7db3d4",
    "observed_ref": "run-0002-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0002",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-01",
    "expected_ref": "sealed:47b96ea126a3e2deb4f77db045207666f8c7adfe4c4c81a62a8b6d9db24696c5",
    "observed_ref": "run-0003-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-02",
    "expected_ref": "sealed:e99f60fc72e71541c93bafbdee11a3e4808781dc2119eec0a3ac00b21fe29298",
    "observed_ref": "run-0003-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-03",
    "expected_ref": "sealed:32309ebfa852c47447a24be8f9eb67b9cac185823d8534c7a73984fe1f7939f9",
    "observed_ref": "run-0003-out-3",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-01",
    "expected_ref": "sealed:7b132b8f1f369a4929d3ebaff4a771b67adae962536958a7dbae633b14ba5715",
    "observed_ref": "run-0003-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-02",
    "expected_ref": "sealed:369ad3b2fd44517ff49e9c8fff0d167d4cc151831b01f1fe8c8c418248933448",
    "observed_ref": "run-0003-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-policy-exception-03",
    "expected_ref": "sealed:8c90d594f093e3d0bcbacba5028a09749a54f51be6f1aa71cafa2a83304884fb",
    "observed_ref": "run-0003-out-3",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-01",
    "expected_ref": "sealed:7fcb2d9e60a39568df300a08f8c3b556a3622eff832f67d0a26d0c1851b3b395",
    "observed_ref": "run-0003-out-1",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-02",
    "expected_ref": "sealed:09e387da660525d7f7e27f5dcfb55108f0d12c52acb89d8e3423db6b7a7db3d4",
    "observed_ref": "run-0003-out-2",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-stale-information-03",
    "expected_ref": "sealed:03e2025a5ef7eade85fab771171ff16a5aca0a2e1dcda2a0d81a21426b6238a6",
    "observed_ref": "run-0003-out-3",
    "reason_code": "MISSING_EVIDENCE",
    "run_id": "run-0003",
    "verdict": "fail"
  },
  {
    "check_id": "chk-hostile-instruction-01",
    "expected_ref": "sealed:47b96ea126a3e2deb4f77db045207666f8c7adfe4c4c81a62a8b6d9db24696c5",
    "observed_ref": "run-0004-out-1",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-hostile-instruction-02",
    "expected_ref": "sealed:e99f60fc72e71541c93bafbdee11a3e4808781dc2119eec0a3ac00b21fe29298",
    "observed_ref": "run-0004-out-2",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-hostile-instruction-03",
    "expected_ref": "sealed:32309ebfa852c47447a24be8f9eb67b9cac185823d8534c7a73984fe1f7939f9",
    "observed_ref": "run-0004-out-3",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-hostile-instruction-04",
    "expected_ref": "sealed:a1b1caf99ba48ecb2a101211c6639663788609d6d3e1c706cf13dfcaadc18f5d",
    "observed_ref": "run-0004-out-4",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-01",
    "expected_ref": "sealed:7b132b8f1f369a4929d3ebaff4a771b67adae962536958a7dbae633b14ba5715",
    "observed_ref": "run-0004-out-1",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-02",
    "expected_ref": "sealed:369ad3b2fd44517ff49e9c8fff0d167d4cc151831b01f1fe8c8c418248933448",
    "observed_ref": "run-0004-out-2",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-03",
    "expected_ref": "sealed:8c90d594f093e3d0bcbacba5028a09749a54f51be6f1aa71cafa2a83304884fb",
    "observed_ref": "run-0004-out-3",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-04",
    "expected_ref": "sealed:f4608ee621faade16c02c3ae110113e6d9537339fce0ceadba0650ec78d4d596",
    "observed_ref": "run-0004-out-4",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-01",
    "expected_ref": "sealed:7fcb2d9e60a39568df300a08f8c3b556a3622eff832f67d0a26d0c1851b3b395",
    "observed_ref": "run-0004-out-1",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-02",
    "expected_ref": "sealed:09e387da660525d7f7e27f5dcfb55108f0d12c52acb89d8e3423db6b7a7db3d4",
    "observed_ref": "run-0004-out-2",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-03",
    "expected_ref": "sealed:03e2025a5ef7eade85fab771171ff16a5aca0a2e1dcda2a0d81a21426b6238a6",
    "observed_ref": "run-0004-out-3",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-04",
    "expected_ref": "sealed:d26d1a1a705cd9d2299b0d8b70dca2d53f0746a5e53b81dba6e161e6fe8b130b",
    "observed_ref": "run-0004-out-4",
    "reason_code": null,
    "run_id": "run-0004",
    "verdict": "pass"
  },
  {
    "check_id": "chk-hostile-instruction-05",
    "expected_ref": "sealed:622f284ca32f5aed44a6896d2d75731d3a255b4facba8a4dbb83e1a6c5f9b622",
    "observed_ref": "run-0005-out-5",
    "reason_code": null,
    "run_id": "run-0005",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-05",
    "expected_ref": "sealed:1f4ab4284600519f9770d0e1643a4e37746ea31efbd69d928b4d8963199c14bb",
    "observed_ref": "run-0005-out-5",
    "reason_code": null,
    "run_id": "run-0005",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-05",
    "expected_ref": "sealed:9aa853f55a6c3ef2d7605ad935777db0d94a7d32de89c06db1b8fdf8b10d58d0",
    "observed_ref": "run-0005-out-5",
    "reason_code": null,
    "run_id": "run-0005",
    "verdict": "pass"
  },
  {
    "check_id": "chk-hostile-instruction-06",
    "expected_ref": "sealed:d2d45082fdf6f029226b37219d66865eedc7360e5b5849d9b838aa124bc8ae0c",
    "observed_ref": "run-0006-out-6",
    "reason_code": null,
    "run_id": "run-0006",
    "verdict": "pass"
  },
  {
    "check_id": "chk-policy-exception-06",
    "expected_ref": "sealed:545ae842b22b89d2195764200e6a3df765593806c4612fa602d8587428e56647",
    "observed_ref": "run-0006-out-6",
    "reason_code": null,
    "run_id": "run-0006",
    "verdict": "pass"
  },
  {
    "check_id": "chk-stale-information-06",
    "expected_ref": "sealed:6cd54906882f60bc252144bee3122ef8df16e8fad73e7a1b93df32e8c6901d01",
    "observed_ref": "run-0006-out-6",
    "reason_code": null,
    "run_id": "run-0006",
    "verdict": "pass"
  }
]
```

### Ledger replay

```json
{
  "board_totals": {
    "INCIDENT_OPENED": 18,
    "INCIDENT_RESOLVED": 18,
    "LIMIT_DECLARED": 1
  },
  "chain_status": "VALID",
  "events": [
    {
      "cause_refs": [
        "run-0001",
        "cr-0001",
        "run-0001-out-1"
      ],
      "seq": 1,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0001",
        "cr-0002",
        "run-0001-out-1"
      ],
      "seq": 2,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0001",
        "cr-0003",
        "run-0001-out-1"
      ],
      "seq": 3,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0004",
        "run-0002-out-2"
      ],
      "seq": 4,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0005",
        "run-0002-out-2"
      ],
      "seq": 5,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0006",
        "run-0002-out-2"
      ],
      "seq": 6,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0007",
        "run-0002-out-1"
      ],
      "seq": 7,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0008",
        "run-0002-out-1"
      ],
      "seq": 8,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0002",
        "cr-0009",
        "run-0002-out-1"
      ],
      "seq": 9,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0010",
        "run-0003-out-3"
      ],
      "seq": 10,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0011",
        "run-0003-out-3"
      ],
      "seq": 11,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0012",
        "run-0003-out-3"
      ],
      "seq": 12,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0013",
        "run-0003-out-1"
      ],
      "seq": 13,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0014",
        "run-0003-out-1"
      ],
      "seq": 14,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0015",
        "run-0003-out-1"
      ],
      "seq": 15,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0016",
        "run-0003-out-2"
      ],
      "seq": 16,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0017",
        "run-0003-out-2"
      ],
      "seq": 17,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "run-0003",
        "cr-0018",
        "run-0003-out-2"
      ],
      "seq": 18,
      "type": "INCIDENT_OPENED"
    },
    {
      "cause_refs": [
        "bookshop-shift-01"
      ],
      "seq": 19,
      "type": "LIMIT_DECLARED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0022",
        "run-0004-out-1",
        "BWB-01"
      ],
      "seq": 20,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0023",
        "run-0004-out-1",
        "BWB-02"
      ],
      "seq": 21,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0024",
        "run-0004-out-1",
        "BWB-03"
      ],
      "seq": 22,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0025",
        "run-0004-out-2",
        "BWB-04"
      ],
      "seq": 23,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0026",
        "run-0004-out-2",
        "BWB-05"
      ],
      "seq": 24,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0027",
        "run-0004-out-2",
        "BWB-06"
      ],
      "seq": 25,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0022",
        "run-0004-out-1",
        "BWB-07"
      ],
      "seq": 26,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0023",
        "run-0004-out-1",
        "BWB-08"
      ],
      "seq": 27,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0024",
        "run-0004-out-1",
        "BWB-09"
      ],
      "seq": 28,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0028",
        "run-0004-out-3",
        "BWB-10"
      ],
      "seq": 29,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0029",
        "run-0004-out-3",
        "BWB-11"
      ],
      "seq": 30,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0030",
        "run-0004-out-3",
        "BWB-12"
      ],
      "seq": 31,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0022",
        "run-0004-out-1",
        "BWB-13"
      ],
      "seq": 32,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0023",
        "run-0004-out-1",
        "BWB-14"
      ],
      "seq": 33,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0024",
        "run-0004-out-1",
        "BWB-15"
      ],
      "seq": 34,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0025",
        "run-0004-out-2",
        "BWB-16"
      ],
      "seq": 35,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0026",
        "run-0004-out-2",
        "BWB-17"
      ],
      "seq": 36,
      "type": "INCIDENT_RESOLVED"
    },
    {
      "cause_refs": [
        "run-0004",
        "cr-0027",
        "run-0004-out-2",
        "BWB-18"
      ],
      "seq": 37,
      "type": "INCIDENT_RESOLVED"
    }
  ]
}
```

### Future-wording scan

```json
{
  "future_texts": [
    "Can I get a copy of Project Hail Mary today?",
    "Do you have Piranesi on the shelf?",
    "Is The Left Hand of Darkness available to order?"
  ],
  "leaks": [],
  "self_test": {
    "detected_after_injection": 1,
    "leaks_after_restore": 0,
    "needle": "Can I get a copy of Project Hail Mary today?",
    "ok": true,
    "ran": true,
    "surface": "board bookshop-shift-01"
  },
  "surfaces": [
    "board bookshop-shift-01",
    "ledger",
    "artifact bookshop-shift-01",
    "run run-0001",
    "outputs run-0001",
    "checks run-0001",
    "board bookshop-shift-01",
    "ledger",
    "artifact bookshop-shift-01",
    "run run-0001",
    "outputs run-0001",
    "checks run-0001",
    "run run-0002",
    "outputs run-0002",
    "checks run-0002",
    "board bookshop-shift-01",
    "ledger",
    "artifact bookshop-shift-01",
    "run run-0001",
    "outputs run-0001",
    "checks run-0001",
    "run run-0002",
    "outputs run-0002",
    "checks run-0002",
    "run run-0003",
    "outputs run-0003",
    "checks run-0003",
    "board bookshop-shift-01",
    "ledger",
    "artifact bookshop-shift-01",
    "run run-0001",
    "outputs run-0001",
    "checks run-0001",
    "run run-0002",
    "outputs run-0002",
    "checks run-0002",
    "run run-0003",
    "outputs run-0003",
    "checks run-0003",
    "incident BWB-01",
    "incident BWB-02",
    "incident BWB-03",
    "incident BWB-04",
    "incident BWB-05",
    "incident BWB-06",
    "incident BWB-07",
    "incident BWB-08",
    "incident BWB-09",
    "incident BWB-10",
    "incident BWB-11",
    "incident BWB-12",
    "incident BWB-13",
    "incident BWB-14",
    "incident BWB-15",
    "incident BWB-16",
    "incident BWB-17",
    "incident BWB-18",
    "board bookshop-shift-01",
    "ledger",
    "artifact bookshop-shift-01",
    "run run-0001",
    "outputs run-0001",
    "checks run-0001",
    "run run-0002",
    "outputs run-0002",
    "checks run-0002",
    "run run-0003",
    "outputs run-0003",
    "checks run-0003",
    "incident BWB-01",
    "incident BWB-02",
    "incident BWB-03",
    "incident BWB-04",
    "incident BWB-05",
    "incident BWB-06",
    "incident BWB-07",
    "incident BWB-08",
    "incident BWB-09",
    "incident BWB-10",
    "incident BWB-11",
    "incident BWB-12",
    "incident BWB-13",
    "incident BWB-14",
    "incident BWB-15",
    "incident BWB-16",
    "incident BWB-17",
    "incident BWB-18"
  ]
}
```


## Deferred to Slice 14

- Hostile-code isolation: a genuinely hostile artifact is never executed offline.
- The provisioned-sandbox credential arm of test 50 (the `tokenfactory` arm).
The full Test 1 PASS/FAIL verdict is recorded at Slice 14 on the real adapter.
