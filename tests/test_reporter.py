import pytest
from scheduler import reporter
from datetime import datetime, timezone


class FakeCursor:
    def __init__(self, changes):
        self._changes = changes

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, length=None):
        return self._changes


class FakeChangesCollection:
    def __init__(self, changes):
        self._changes = changes

    def find(self, *args, **kwargs):
        # ignore query args for tests
        return FakeCursor(self._changes)


class FakeDB:
    def __init__(self, changes):
        self.changes = FakeChangesCollection(changes)


@pytest.mark.asyncio
async def test_generate_daily_change_report_json(monkeypatch):
    fake_changes = [{
        "_id": object(),
        "source_url": "http://example.com/book1",
            "changed_at": datetime.now(timezone.utc),
        "old_fingerprint": "oldfp",
        "new_fingerprint": "newfp",
        "old": {"_id": object(), "title": "Old", "price_including_tax": 10.0, "raw_html_snapshot": "<html>old</html>"},
        "new": {"_id": object(), "title": "New", "price_including_tax": 9.0, "raw_html_snapshot": "<html>new</html>"},
    }]

    # Replace the db used in reporter with a fake one
    monkeypatch.setattr(reporter, "db", FakeDB(fake_changes))

    res = await reporter.generate_daily_change_report(format="json")
    assert isinstance(res, list)
    assert res[0]["source_url"] == "http://example.com/book1"
    # _id and nested _id should be converted to str
    assert isinstance(res[0]["_id"], str)
    assert isinstance(res[0]["old"]["_id"], str)
    # raw_html_snapshot should still be present in JSON output
    assert "raw_html_snapshot" in res[0]["old"]


@pytest.mark.asyncio
async def test_generate_daily_change_report_csv(monkeypatch):
    fake_changes = [{
        "_id": object(),
        "source_url": "http://example.com/book2",
            "changed_at": datetime.now(timezone.utc),
        "old_fingerprint": "oldfp2",
        "new_fingerprint": "newfp2",
        "old": {"_id": object(), "title": "Old2", "price_including_tax": 15.0, "raw_html_snapshot": "<html>old2</html>"},
        "new": {"_id": object(), "title": "New2", "price_including_tax": 14.0, "raw_html_snapshot": "<html>new2</html>"},
    }]

    monkeypatch.setattr(reporter, "db", FakeDB(fake_changes))

    csv_text = await reporter.generate_daily_change_report(format="csv")
    assert isinstance(csv_text, str)
    # header should include source_url and old.title/new.title fields
    assert "source_url" in csv_text
    assert "old.title" in csv_text or "title" in csv_text
    # raw_html_snapshot must be excluded from CSV output
    assert "raw_html_snapshot" not in csv_text


@pytest.mark.asyncio
async def test_generate_daily_change_report_empty_csv(monkeypatch):
    monkeypatch.setattr(reporter, "db", FakeDB([]))
    csv_text = await reporter.generate_daily_change_report(format="csv")
    assert csv_text == ""
