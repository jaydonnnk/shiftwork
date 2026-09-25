import importlib.util

from fastapi.testclient import TestClient


def test_preview_uses_executed_slice8_fixture_in_an_isolated_database(tmp_path, select_version_for_test):
    assert importlib.util.find_spec("demos.client") is not None, "isolated preview is not implemented"
    from demos.client import create_preview

    # S10 made operation run the exact selected version and S17 owns the real
    # selection route, so the executed-run precondition is installed from the test
    # layer. The shipped demo fabricates no choice.
    preview = create_preview(
        str(tmp_path / "preview.db"), selection_factory=select_version_for_test
    )
    with TestClient(preview) as client:
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_run"]["state"] == "FINALIZED"
        assert board["latest_run"]["adapter"] == "local_process"
        assert board["requests_run"] == 2
        assert board["attempts_remaining"] == 1
        assert board["incidents"]
        assert board["latest_version"]["created_by"] == "learner"
        assert client.get("/").status_code == 200
