"""Small deterministic lexical rankers shared by the API and evaluator."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from itertools import islice

from .models import validate_documents

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_K1 = 1.2
_B = 0.75

RANKING_POLICY = {
    "tokenization": "NFKC + casefold + [^\\W_]+",
    "document_text": "title + single space + body",
    "title_boost": 1.0,
    "query_terms": "unique",
    "bm25": {
        "k1": _K1,
        "b": _B,
        "idf": "log(1+(N-df+0.5)/(df+0.5))",
        "score": "sum idf*tf*(k1+1)/(tf+k1*(1-b+b*dl/avgdl))",
    },
    "baseline": "count of distinct query tokens present in document",
    "ties": "document id ascending",
    "zero_scores": "omitted",
}


def tokenize(text: str) -> list[str]:
    """Normalize Unicode, casefold, and split on nonword characters or underscores."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return _TOKEN.findall(unicodedata.normalize("NFKC", text).casefold())


def _documents(documents: Iterable[dict]) -> list[dict]:
    if isinstance(documents, (str, bytes, dict)):
        raise ValueError("documents must be an iterable of document objects")
    try:
        items = list(islice(iter(documents), 501))
    except TypeError as exc:
        raise ValueError("documents must be an iterable of document objects") from exc
    return validate_documents(items)


def _query(query: str) -> list[str]:
    if not isinstance(query, str) or len(query) > 512:
        raise ValueError("query must be a string of at most 512 characters")
    return sorted(set(tokenize(query)))


def _validate_k(k: int) -> None:
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 20:
        raise ValueError("k must be an integer from 1 to 20")


def rank(docs: Iterable[dict], query: str, *, method: str = "bm25", k: int = 5) -> list[dict]:
    """Rank documents by fixed BM25 or distinct-token overlap, omitting zero hits."""
    _validate_k(k)
    if method not in {"bm25", "overlap"}:
        raise ValueError("method must be 'bm25' or 'overlap'")
    documents = _documents(docs)
    terms = _query(query)
    if not terms:
        return []

    tokenized = [tokenize(doc["title"] + " " + doc["body"]) for doc in documents]
    counters = [Counter(tokens) for tokens in tokenized]
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / len(lengths)
    if method == "bm25" and average_length == 0:
        return []

    frequencies = {term: sum(counter.get(term, 0) > 0 for counter in counters) for term in terms}
    scored: list[dict] = []
    for doc, counter, doc_length in zip(documents, counters, lengths, strict=True):
        if method == "overlap":
            score = float(sum(counter.get(term, 0) > 0 for term in terms))
        else:
            parts = []
            for term in terms:
                tf = counter.get(term, 0)
                if not tf:
                    continue
                df = frequencies[term]
                idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
                norm = tf + _K1 * (1 - _B + _B * doc_length / average_length)
                parts.append(idf * tf * (_K1 + 1) / norm)
            score = math.fsum(parts)
        if score > 0 and math.isfinite(score):
            scored.append({"id": doc["id"], "score": score})
    scored.sort(key=lambda hit: (-hit["score"], hit["id"]))
    return scored[:k]
