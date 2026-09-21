import importlib.util

from fastapi.testclient import TestClient


def test_preview_uses_executed_slice8_fixture_in_an_isolated_database(tmp_path):
    assert importlib.util.find_spec("demos.client") is not None, "isolated preview is not implemented"
    from demos.client import create_preview

    with TestClient(create_preview(str(tmp_path / "preview.db"))) as client:
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_run"]["state"] == "FINALIZED"
        assert board["latest_run"]["adapter"] == "local_process"
        assert board["requests_run"] == 2
        assert board["attempts_remaining"] == 1
        assert board["incidents"]
        assert board["latest_version"]["created_by"] == "learner"
        assert client.get("/").status_code == 200
