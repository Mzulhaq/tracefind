import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from tracefind.models import validate_documents
from tracefind.store import Conflict, Store


def doc(id="reset", body="Reset your password using a recovery code."):
    return {"id": id, "title": "Account recovery", "body": body, "source": f"handbook://{id}"}


def test_durable_canonical_revision_and_order_independence(tmp_path):
    path = tmp_path / "search.db"
    store = Store(path)
    docs = [doc("b"), doc("a")]
    result = store.replace(docs)
    snapshot = Store(path).snapshot()
    assert snapshot[1] == sorted(docs, key=lambda d: d["id"])
    expected = hashlib.sha256(
        json.dumps(snapshot[1], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert result == {"revision": expected, "count": 2, "changed": True}
    assert store.replace(docs[::-1]) == {**result, "changed": False}
    assert snapshot[0] == expected


def test_replacement_removes_old_documents_and_cas_is_checked_first(tmp_path):
    store = Store(tmp_path / "search.db")
    assert store.snapshot() == (None, [])
    first = store.replace([doc()])
    second = store.replace([doc("new")], expected_revision=first["revision"])
    assert store.snapshot()[1] == [doc("new")]
    with pytest.raises(Conflict):
        store.replace([doc("new")], expected_revision=first["revision"])
    assert store.snapshot()[0] == second["revision"]


def test_failed_replacement_rolls_back_deletion_and_revision(tmp_path):
    store = Store(tmp_path / "search.db")
    store.replace([doc()])
    original = store.snapshot()
    with closing(sqlite3.connect(store.path)) as connection:
        connection.execute("""CREATE TRIGGER reject_new BEFORE INSERT ON documents
        WHEN NEW.id='bad' BEGIN SELECT RAISE(ABORT,'injected'); END""")
        connection.commit()
    with pytest.raises(sqlite3.IntegrityError, match="injected"):
        store.replace([doc("good"), doc("bad")])
    assert store.snapshot() == original


def test_competing_cas_writers_have_exactly_one_winner(tmp_path):
    store = Store(tmp_path / "search.db")
    revision = store.replace([doc()])["revision"]
    barrier = threading.Barrier(2)

    def replace(id):
        barrier.wait(timeout=10)
        try:
            return store.replace([doc(id)], expected_revision=revision)
        except Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(replace, ["one", "two"]))
    assert results.count("conflict") == 1
    winner = next(r for r in results if r != "conflict")
    assert store.snapshot()[0] == winner["revision"]


def test_concurrent_readers_never_mix_revision_and_documents(tmp_path):
    store = Store(tmp_path / "search.db")
    versions = [[doc("a", "first version")], [doc("b", "second version")]]
    expected = {store.replace(d)["revision"]: d for d in versions}
    start = threading.Barrier(2)

    def writer():
        start.wait(timeout=10)
        for i in range(25):
            store.replace(versions[i % 2])

    def reader():
        start.wait(timeout=10)
        for _ in range(25):
            revision, documents = store.snapshot()
            assert documents == expected[revision]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(writer), pool.submit(reader)]
        for future in futures:
            future.result(timeout=20)


@pytest.mark.parametrize(
    "documents",
    [
        [],
        [doc(), doc()],
        [doc(id="bad/id")],
        [{**doc(), "body": " "}],
        [{**doc(), "extra": "x"}],
        [{**doc(), "title": 123}],
        [{**doc(), "body": "x" * 8001}],
        [doc(str(i)) for i in range(501)],
        [doc(str(i), "x" * 8000) for i in range(130)],
    ],
)
def test_invalid_corpus_never_changes_existing_data(tmp_path, documents):
    store = Store(tmp_path / "search.db")
    store.replace([doc()])
    before = store.snapshot()
    with pytest.raises(ValueError):
        store.replace(documents)
    assert store.snapshot() == before


def test_validation_returns_independent_copies():
    original = [doc()]
    validated = validate_documents(original)
    original[0]["body"] = "changed"
    assert validated[0]["body"] != "changed"


def test_foreign_database_is_rejected_without_changes(tmp_path):
    path = tmp_path / "foreign.db"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE unrelated(value TEXT)")
        connection.commit()
    with pytest.raises(ValueError, match="TraceFind"):
        Store(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == [("unrelated",)]
