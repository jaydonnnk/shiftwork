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
