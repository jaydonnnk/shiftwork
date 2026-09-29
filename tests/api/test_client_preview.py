import importlib.util

from fastapi.testclient import TestClient


def test_preview_uses_labelled_starter_and_real_selection_route(tmp_path):
    assert importlib.util.find_spec("demos.client") is not None, "isolated preview is not implemented"
    from demos.client import create_preview

    preview = create_preview(str(tmp_path / "preview.db"))
    with TestClient(preview) as client:
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_run"]["state"] == "FINALIZED"
        assert board["latest_run"]["adapter"] == "recorded"
        assert board["requests_run"] == 2
        assert board["attempts_remaining"] == 1
        assert board["incidents"]
        assert board["operating_selection"]["kind"] == "STARTER_BASELINE"
        assert len(client.get("/api/engagements/bookshop/selections").json()) == 1
        assert client.get("/").status_code == 200
