from html.parser import HTMLParser

from fastapi.testclient import TestClient

from shiftwork.app import create_app


class Shell(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.stations = set()
        self.regions = set()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-station" in attrs:
            self.stations.add(attrs["data-station"])
        if "data-synthetic-region" in attrs:
            self.regions.add(attrs["data-synthetic-region"])


def test_served_client_has_keyboard_station_controls_and_labelled_regions(tmp_path):
    with TestClient(create_app(str(tmp_path / "shell.db"))) as client:
        response = client.get("/")
        assert response.status_code == 200
        shell = Shell(response.text)
        assert shell.stations == {"owner", "service", "customers", "pipeline", "evaluator", "ledger", "repair", "investigate", "compare"}
        assert shell.regions >= {"board", "run", "incidents", "ledger", "source", "diagnostic", "comparison", "comparison-slots"}
        assert "Synthetic scenario" in response.text
        assert "junior applied AI engineer" in response.text
        for asset in ("app.js", "styles.css", "room.svg"):
            assert client.get("/" + asset).status_code == 200
