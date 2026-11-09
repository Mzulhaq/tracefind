"""Read-only HTTP search over one revision-consistent corpus snapshot."""

import sqlite3
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from tracefind.retrieval import rank
from tracefind.store import Store


class EmptyCorpus(ValueError):
    pass


def search_snapshot(store: Store, query: str, method: str = "bm25", k: int = 5) -> dict:
    revision, documents = store.snapshot()
    if revision is None:
        raise EmptyCorpus("Load a corpus before searching")
    indexed = {document["id"]: document for document in documents}
    hits = []
    for hit in rank(documents, query, method=method, k=k):
        document = indexed[hit["id"]]
        hits.append(
            {
                "id": document["id"],
                "title": document["title"],
                "source": document["source"],
                "text": document["body"],
                "score": hit["score"],
            }
        )
    return {"revision": revision, "query": query, "method": method, "hits": hits}


def create_app(db_path) -> FastAPI:
    app = FastAPI(
        title="TraceFind",
        version="0.1.0",
        description="Read-only lexical retrieval. Scores are not confidence probabilities.",
    )
    app.state.store = Store(db_path)

    @app.exception_handler(sqlite3.Error)
    def database_error(request: Request, exc: sqlite3.Error):
        return JSONResponse(status_code=503, content={"detail": "Corpus storage unavailable"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/v1/corpus")
    def corpus():
        revision, documents = app.state.store.snapshot()
        return {"revision": revision, "count": len(documents)}

    @app.get("/v1/search")
    def search(
        q: Annotated[str, Query(max_length=512)],
        k: Annotated[int, Query(ge=1, le=20)] = 5,
        method: Literal["bm25", "overlap"] = "bm25",
    ):
        try:
            return search_snapshot(app.state.store, q, method, k)
        except EmptyCorpus as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Invalid search input") from error

    return app
