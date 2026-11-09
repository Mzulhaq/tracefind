"""Exercise real loopback HTTP and evaluate the fixed synthetic corpus, without external calls."""

import json
import socket
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import uvicorn

from tracefind.api import create_app
from tracefind.evaluation import evaluate
from tracefind.models import read_json, validate_documents
from tracefind.retrieval import rank
from tracefind.store import Store

ROOT = Path(__file__).resolve().parents[1]


def main():
    documents = validate_documents(read_json(ROOT / "data/corpus.json"))
    cases = read_json(ROOT / "data/queries.json")
    expected_documents = {document["id"]: document for document in documents}
    with tempfile.TemporaryDirectory(prefix="tracefind-demo-") as temporary:
        db = Path(temporary) / "search.db"
        store = Store(db)
        loaded = store.replace(documents)
        assert loaded["count"] == 20
        assert not store.replace(documents[::-1])["changed"]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            base = f"http://127.0.0.1:{listener.getsockname()[1]}"
            server = uvicorn.Server(
                uvicorn.Config(create_app(db), log_level="error", access_log=False)
            )
            thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            thread.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.02)
                if not server.started:
                    raise RuntimeError("Demo HTTP server did not start")

                # Disable proxy discovery: these requests must stay on loopback.
                client = urllib.request.build_opener(urllib.request.ProxyHandler({}))

                def get(path):
                    with client.open(base + path, timeout=10) as response:
                        return json.load(response)

                assert get("/health") == {"status": "ok"}
                assert get("/v1/corpus") == {"revision": loaded["revision"], "count": 20}
                for method in ("bm25", "overlap"):
                    query = cases[0]["query"]
                    params = urllib.parse.urlencode({"q": query, "method": method, "k": 3})
                    result = get("/v1/search?" + params)
                    assert result["revision"] == loaded["revision"]
                    assert [{"id": h["id"], "score": h["score"]} for h in result["hits"]] == rank(
                        documents, query, method=method, k=3
                    )
                    for hit in result["hits"]:
                        assert hit["text"] == expected_documents[hit["id"]]["body"]
                        assert hit["source"] == expected_documents[hit["id"]]["source"]
                assert get("/v1/search?q=zzzzzzquartzxylophone")["hits"] == []
                report = evaluate(documents, cases, k=3)
                assert report["case_count"] == 24
                assert report["answerable_count"] == 20
                assert report["unanswerable_count"] == 4
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                if thread.is_alive():
                    raise RuntimeError("Demo HTTP server did not stop")
    summary = {
        method: {key: value for key, value in metrics.items() if key != "per_query"}
        for method, metrics in report["methods"].items()
    }
    print(
        json.dumps(
            {
                "result": "PASS",
                "documents": 20,
                "queries": 24,
                "http_matches_offline": True,
                "citations_match_source": True,
                "revision": loaded["revision"],
                "evaluation_at_3": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
