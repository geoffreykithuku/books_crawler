from fastapi.testclient import TestClient
from api import main as api_main
from api.main import API_KEY, app
import pytest

client = TestClient(app)


@pytest.mark.parametrize("fmt,expected_status", [("json",200),("csv",200)])
def test_daily_report_endpoint(monkeypatch, fmt, expected_status):
    async def fake_report(format: str = "json"):
        if format == "json":
            return [{"source_url": "http://example.com/book1", "changed_at": "2025-11-10T00:00:00Z"}]
        else:
            return "source_url,changed_at\nhttp://example.com/book1,2025-11-10T00:00:00Z\n"

    # monkeypatch the function used by the API (imported into api.main)
    monkeypatch.setattr(api_main, "generate_daily_change_report", fake_report)

    headers = {"X-API-Key": API_KEY}
    r = client.get(f"/report/daily_changes?format={fmt}", headers=headers)
    assert r.status_code == expected_status
    if fmt == "json":
        assert isinstance(r.json(), list)
        assert r.json()[0]["source_url"] == "http://example.com/book1"
    else:
        # CSV response is returned via JSONResponse (string body) with media_type text/csv;
        # strip surrounding quotes if present
        text = r.text
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        assert "source_url" in text
        assert "http://example.com/book1" in text
