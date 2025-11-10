
import pytest
from fastapi.testclient import TestClient
from api.main import app
from db.client import db
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("API_KEY","testkey123")

client = TestClient(app)

def test_books_requires_api_key():
    r = client.get("/books")
    assert r.status_code == 422 or r.status_code == 401  # missing header

def test_books_with_key(monkeypatch):
    # Provide a fake cursor that avoids touching Motor / MongoDB during tests
    class FakeCursor:
        def __init__(self):
            self._docs = []
        def sort(self, *args, **kwargs):
            return self
        def skip(self, n):
            return self
        def limit(self, n):
            return self
        async def to_list(self, length=None):
            return self._docs

    monkeypatch.setattr(db, "books", type("B", (), {"find": lambda *args, **kwargs: FakeCursor()}))

    r = client.get("/books", headers={"x-api-key": API_KEY})
    assert r.status_code == 200
    assert "data" in r.json()
