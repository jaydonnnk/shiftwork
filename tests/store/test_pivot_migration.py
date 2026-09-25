"""S10: migrate only a copy of schema-v5 history and keep old values intact."""

import hashlib
import shutil
import sqlite3

import pytest

from demos.final_pivot import assert_v5_rows_preserved, create_v5_sample, snapshot_v5_rows
from shiftwork.store import db


def _copy_v5(tmp_path, *, with_run=True):
    original = tmp_path / "original-v5.db"
    copied = tmp_path / "copy-for-v6.db"
    create_v5_sample(original, with_run=with_run)
    shutil.copy2(original, copied)
    source = sqlite3.connect(original)
    try:
        before = snapshot_v5_rows(source)
    finally:
        source.close()
    return original, copied, before


def test_v5_to_v6_preserves_every_legacy_blob_hash_and_row_count(tmp_path):
    original, copied, before = _copy_v5(tmp_path)
    original_file_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    assert len(before["runs"][1]) == 1
    assert len(before["run_outputs"][1]) == 1
    assert len(before["check_results"][1]) == 1
    assert len(before["incidents"][1]) == 1
    assert len(before["ledger_events"][1]) == 1
    assert len(before["rotation_draws"][1]) == 1

    conn = db.connect(copied)
    try:
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 6
        assert_v5_rows_preserved(conn, before)
        run = conn.execute("SELECT * FROM runs WHERE id='run-v5-0001'").fetchone()
        assert run["purpose"] == "LEGACY_OPERATION"
        assert run["evidence_mode"] == "RECORDED_INSPECTION"
        assert run["context_id"] is None
        assert run["experiment_id"] is None
        assert run["trial_slot_id"] is None
        assert run["selection_id"] is None
        assert conn.execute("SELECT opening_mode FROM shifts WHERE seq=1").fetchone()[0] is None
    finally:
        conn.close()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_file_hash


@pytest.mark.parametrize("with_run", [True, False])
def test_v5_migration_creates_no_experiment_or_selection(tmp_path, with_run):
    _, copied, before = _copy_v5(tmp_path, with_run=with_run)
    conn = db.connect(copied)
    try:
        db.ensure_schema(conn)
        assert_v5_rows_preserved(conn, before)
        assert conn.execute("SELECT COUNT(*) FROM operating_selections").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == int(with_run)
        assert conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0] == int(with_run)
        assert conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == int(with_run)
        assert conn.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0] == 1
        if not with_run:
            # The later S13 public bootstrap remains possible in policy but S10
            # neither reserves it nor fabricates its missing source request.
            assert conn.execute("SELECT COUNT(*) FROM run_outputs").fetchone()[0] == 0
    finally:
        conn.close()


def test_v6_migration_is_atomic_and_idempotent(tmp_path):
    _, copied, before = _copy_v5(tmp_path)
    conn = db.connect(copied)
    alter_count = 0

    def deny_second_alter(action, _arg1, _arg2, _database, _trigger):
        nonlocal alter_count
        if action == sqlite3.SQLITE_ALTER_TABLE:
            alter_count += 1
            if alter_count == 2:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    try:
        conn.set_authorizer(deny_second_alter)
        with pytest.raises(sqlite3.DatabaseError):
            db.ensure_schema(conn)
        assert alter_count >= 2, "fault did not reach a second v6 DDL statement"
        conn.set_authorizer(None)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
        assert "opening_mode" not in {
            row[1] for row in conn.execute("PRAGMA table_info(shifts)")
        }
        assert_v5_rows_preserved(conn, before)
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 6
        assert_v5_rows_preserved(conn, before)
        first_schema = tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"))
        db.ensure_schema(conn)
        assert tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name")) == first_schema
        assert_v5_rows_preserved(conn, before)
    finally:
        conn.set_authorizer(None)
        conn.close()


def test_unknown_schema_version_fails_closed(tmp_path):
    _, copied, before = _copy_v5(tmp_path)
    conn = db.connect(copied)
    try:
        conn.execute("PRAGMA user_version = 99")
        schema_before = tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"))
        with pytest.raises(RuntimeError, match="version 99"):
            db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 99
        assert tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name")) == schema_before
        assert_v5_rows_preserved(conn, before)
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("adapter", "expected_mode"),
    [("local_process", "TRUSTED_LOCAL"), ("tokenfactory", None)],
)
def test_legacy_adapter_label_does_not_claim_fresh_live_execution(
    tmp_path, adapter, expected_mode
):
    original, copied, _ = _copy_v5(tmp_path)
    for path in (original, copied):
        conn = sqlite3.connect(path)
        try:
            conn.execute("UPDATE runs SET adapter = ?", (adapter,))
            conn.commit()
        finally:
            conn.close()
    source = sqlite3.connect(original)
    try:
        before = snapshot_v5_rows(source)
    finally:
        source.close()
    conn = db.connect(copied)
    try:
        db.ensure_schema(conn)
        assert_v5_rows_preserved(conn, before)
        run = conn.execute("SELECT adapter, purpose, evidence_mode FROM runs").fetchone()
        assert run["adapter"] == adapter
        assert run["purpose"] == "LEGACY_OPERATION"
        assert run["evidence_mode"] == expected_mode
    finally:
        conn.close()


# Slice 11: Gate 3 S4 assigns every pivot table to schema version 6, but a table's
# DDL lands with the slice that first uses it. These tests pin the completion and
# the reopen reconciliation that keeps an already-v6 database from staying
# silently incomplete.

S11_V6_TABLES = (
    "execution_contexts",
    "execution_observations",
    "investigations",
    "run_assessments",
    "task_assessments",
)

S11_V6_TRIGGERS = (
    "execution_observations_no_delete",
    "execution_observations_no_update",
    "investigations_no_delete",
    "investigations_no_update",
    "investigations_revision_same_shift",
    "run_assessments_no_delete",
    "run_assessments_no_update",
)


def _object_names(conn, object_type):
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", (object_type,)
        )
    }


def _ddl_by_name(conn, names):
    return dict(
        conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE name IN ({})".format(
                ",".join("?" for _ in names)
            ),
            tuple(names),
        ).fetchall()
    )


def _migrated_v6(tmp_path):
    _, copied, before = _copy_v5(tmp_path)
    conn = db.connect(copied)
    db.ensure_schema(conn)
    return conn, before


def _insert_investigation(conn, inv_id, shift_id, run_id, revision_of_id=None):
    conn.execute(
        "INSERT INTO investigations (id, shift_id, source_run_id, source_request_ordinal,"
        " cause, falsifier, public_test, revision_of_id, created_at)"
        " VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)",
        (
            inv_id,
            shift_id,
            run_id,
            "the keyword router treats the pound symbol as a price question",
            "a request with no currency symbol still omits the collection task",
            "assert a result exists for every required task",
            revision_of_id,
            "2026-09-25T09:00:00+00:00",
        ),
    )


def test_v6_migration_creates_the_slice_11_pivot_tables(tmp_path):
    conn, before = _migrated_v6(tmp_path)
    try:
        tables = _object_names(conn, "table")
        assert [name for name in S11_V6_TABLES if name not in tables] == []
        assert_v5_rows_preserved(conn, before)
    finally:
        conn.close()


def test_already_v6_database_gains_missing_tables_without_touching_history(tmp_path):
    """Reopening an older v6 database completes it instead of returning early.

    Dropping the five tables models a database migrated by the Slice 10 build,
    which reported user_version 6 while lacking them. Before the reconciliation,
    ensure_schema returned at once and the tables never arrived.
    """
    conn, before = _migrated_v6(tmp_path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 6
        for name in S11_V6_TABLES:
            conn.execute(f"DROP TABLE {name}")
        conn.commit()
        assert _object_names(conn, "table").isdisjoint(S11_V6_TABLES)

        db.ensure_schema(conn)

        assert conn.execute("PRAGMA user_version").fetchone()[0] == 6
        tables = _object_names(conn, "table")
        assert [name for name in S11_V6_TABLES if name not in tables] == []
        assert_v5_rows_preserved(conn, before)
    finally:
        conn.close()


def test_reconcile_completes_tables_without_rerunning_v6_backfills(tmp_path):
    """The reopen path is table DDL only; it must not re-apply v6.sql.

    v6.sql carries ALTER TABLE and an evidence_mode backfill, neither of which is
    idempotent. Clearing the backfilled column and reopening proves the
    reconciliation left it cleared rather than silently restoring it.
    """
    conn, _ = _migrated_v6(tmp_path)
    try:
        assert conn.execute("SELECT evidence_mode FROM runs").fetchone()[0] is not None
        conn.execute("UPDATE runs SET evidence_mode = NULL")
        conn.commit()

        db.ensure_schema(conn)

        assert conn.execute("SELECT evidence_mode FROM runs").fetchone()[0] is None
    finally:
        conn.close()


def test_fresh_and_migrated_paths_define_the_s11_objects_identically(tmp_path):
    fresh_conn = db.connect(tmp_path / "fresh-v6.db")
    try:
        db.ensure_schema(fresh_conn)
        fresh = _ddl_by_name(fresh_conn, S11_V6_TABLES + S11_V6_TRIGGERS)
    finally:
        fresh_conn.close()

    migrated_conn, _ = _migrated_v6(tmp_path)
    try:
        migrated = _ddl_by_name(migrated_conn, S11_V6_TABLES + S11_V6_TRIGGERS)
    finally:
        migrated_conn.close()

    assert sorted(fresh) == sorted(S11_V6_TABLES + S11_V6_TRIGGERS)
    assert fresh == migrated, "the two schema paths drifted for a v6 object"


def test_investigations_reject_update_and_delete(tmp_path):
    conn, _ = _migrated_v6(tmp_path)
    try:
        shift_id = conn.execute("SELECT id FROM shifts ORDER BY seq LIMIT 1").fetchone()[0]
        run_id = conn.execute("SELECT id FROM runs LIMIT 1").fetchone()[0]
        _insert_investigation(conn, "inv-1", shift_id, run_id)
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE investigations SET cause = 'rewritten history'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM investigations WHERE id = 'inv-1'")

        row = conn.execute("SELECT cause FROM investigations WHERE id = 'inv-1'").fetchone()
        assert row[0] == "the keyword router treats the pound symbol as a price question"
    finally:
        conn.close()


def test_investigation_revision_must_reference_the_same_shift(tmp_path):
    conn, _ = _migrated_v6(tmp_path)
    try:
        shift_id = conn.execute("SELECT id FROM shifts ORDER BY seq LIMIT 1").fetchone()[0]
        run_id = conn.execute("SELECT id FROM runs LIMIT 1").fetchone()[0]
        slug = conn.execute("SELECT engagement_slug FROM shifts WHERE id = ?", (shift_id,)).fetchone()[0]
        conn.execute(
            "INSERT INTO shifts (id, engagement_slug, seq, state, opened_at, opening_mode)"
            " VALUES ('shift-other', ?, 2, 'open', '2026-09-25T10:00:00+00:00', 'STANDARD')",
            (slug,),
        )
        _insert_investigation(conn, "inv-1", shift_id, run_id)
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError, match="same shift"):
            _insert_investigation(conn, "inv-stolen", "shift-other", run_id, revision_of_id="inv-1")

        _insert_investigation(conn, "inv-2", shift_id, run_id, revision_of_id="inv-1")
        conn.commit()
        rows = dict(
            conn.execute("SELECT id, revision_of_id FROM investigations ORDER BY id").fetchall()
        )
        assert rows == {"inv-1": None, "inv-2": "inv-1"}, "a revision must keep its parent row"
    finally:
        conn.close()


def test_observations_and_run_assessments_reject_mutation(tmp_path):
    conn, _ = _migrated_v6(tmp_path)
    try:
        run_id = conn.execute("SELECT id FROM runs LIMIT 1").fetchone()[0]
        conn.execute(
            "INSERT INTO execution_observations (id, run_id, request_ordinal, ordinal, kind,"
            " public_payload_json, raw_payload_ref, measured_at)"
            " VALUES ('obs-1', ?, 1, 1, 'INTERPRETATION', '{}', 'raw:obs-1',"
            " '2026-09-25T09:00:00+00:00')",
            (run_id,),
        )
        conn.execute(
            "INSERT INTO run_assessments (run_id, context_hash, complete_request_count,"
            " expected_request_count, mandatory_pass, rule_version, assessed_at)"
            " VALUES (?, 'ctx-hash', 0, 1, 0, 'evaluator-v1', '2026-09-25T09:00:00+00:00')",
            (run_id,),
        )
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE execution_observations SET kind = 'USAGE'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM execution_observations")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE run_assessments SET mandatory_pass = 1")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM run_assessments")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO execution_observations (id, run_id, request_ordinal, ordinal, kind,"
                " public_payload_json, raw_payload_ref, measured_at)"
                " VALUES ('obs-2', ?, 1, 1, 'USAGE', '{}', 'raw:obs-2',"
                " '2026-09-25T09:00:00+00:00')",
                (run_id,),
            )
    finally:
        conn.close()
