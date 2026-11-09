import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.test_store import doc
from tracefind.api import create_app
from tracefind.store import Store


def test_empty_corpus_liveness_and_search_conflict(tmp_path):
    with TestClient(create_app(tmp_path / "search.db")) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/v1/corpus").json() == {"revision": None, "count": 0}
        assert client.get("/v1/search", params={"q": "password"}).status_code == 409


def test_api_returns_exact_citations_from_a_versioned_corpus(tmp_path):
    path = tmp_path / "search.db"
    store = Store(path)
    documents = [doc(), doc("billing", "Invoices are available every month.")]
    revision = store.replace(documents)["revision"]
    with TestClient(create_app(path)) as client:
        for method in ("bm25", "overlap"):
            response = client.get("/v1/search", params={"q": "password", "method": method})
            assert response.status_code == 200
            payload = response.json()
            assert payload["revision"] == revision
            assert payload["method"] == method
            assert payload["hits"][0]["id"] == "reset"
            assert payload["hits"][0]["text"] == documents[0]["body"]
            assert payload["hits"][0]["source"] == documents[0]["source"]
        assert client.get("/v1/search", params={"q": "volcano"}).json()["hits"] == []
        assert client.get("/v1/search", params={"q": "!!!"}).json()["hits"] == []
        assert client.post("/v1/corpus", json=documents).status_code == 405


@pytest.mark.parametrize(
    "params",
    [
        {"q": "x", "k": 0},
        {"q": "x", "k": 21},
        {"q": "x", "k": "1.5"},
        {"q": "x", "method": "model"},
        {"q": "x" * 513},
        {},
    ],
)
def test_invalid_search_parameters_are_rejected(tmp_path, params):
    with TestClient(create_app(tmp_path / "search.db")) as client:
        assert client.get("/v1/search", params=params).status_code == 422


def test_database_failure_has_generic_error(tmp_path, monkeypatch):
    app = create_app(tmp_path / "search.db")

    def fail():
        raise sqlite3.OperationalError("private path or internal message")

    monkeypatch.setattr(app.state.store, "snapshot", fail)
    with TestClient(app) as client:
        response = client.get("/v1/search", params={"q": "anything"})
        assert response.status_code == 503
        assert "private" not in response.text
