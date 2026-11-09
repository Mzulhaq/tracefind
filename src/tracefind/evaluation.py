"""Deterministic graded-relevance evaluation for the shared lexical rankers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .retrieval import RANKING_POLICY, _documents, _validate_k, rank

_CASE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}\Z", re.ASCII)
_METHODS = ("bm25", "overlap")


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_cases(cases: Sequence[dict], known_ids: set[str]) -> list[dict]:
    if isinstance(cases, (str, bytes, Mapping)) or not isinstance(cases, Sequence):
        raise ValueError("cases must be a nonempty sequence")
    if not cases:
        raise ValueError("cases must be a nonempty sequence")
    output: list[dict] = []
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "query", "relevant"}:
            raise ValueError("each case must contain exactly id, query, and relevant")
        case_id = case["id"]
        if not isinstance(case_id, str) or not _CASE_ID.fullmatch(case_id):
            raise ValueError("case id must be 1 to 64 allowed ASCII characters")
        if case_id in seen:
            raise ValueError("case ids must be unique")
        seen.add(case_id)
        query = case["query"]
        if not isinstance(query, str) or len(query) > 512:
            raise ValueError("case query must be a string of at most 512 characters")
        relevant = case["relevant"]
        if not isinstance(relevant, dict):
            raise ValueError("relevant must map known document ids to grades")
        checked: dict[str, int] = {}
        for doc_id, grade in relevant.items():
            if not isinstance(doc_id, str) or doc_id not in known_ids:
                raise ValueError("relevance labels must use known document ids")
            if isinstance(grade, bool) or not isinstance(grade, int) or not 1 <= grade <= 3:
                raise ValueError("relevance grades must be integers from 1 to 3")
            checked[doc_id] = grade
        output.append({"id": case_id, "query": query, "relevant": checked})
    return sorted(output, key=lambda case: case["id"])


def _deduplicate_ranking(ranking: Sequence[dict], known_ids: set[str], k: int) -> list[dict]:
    output: list[dict] = []
    seen: set[str] = set()
    for hit in ranking:
        if not isinstance(hit, dict) or set(hit) != {"id", "score"}:
            raise ValueError("ranker returned an invalid hit")
        doc_id = hit["id"]
        score = hit["score"]
        if not isinstance(doc_id, str) or doc_id not in known_ids:
            raise ValueError("ranker returned an unknown document id")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
        ):
            raise ValueError("ranker returned a non-finite score")
        if doc_id not in seen:
            seen.add(doc_id)
            output.append({"id": doc_id, "score": float(score)})
            if len(output) == k:
                break
    return output


def _case_metrics(ranking: list[dict], relevant: dict[str, int], k: int) -> dict:
    answerable = bool(relevant)
    if not answerable:
        failures = (
            [
                {
                    "code": "unanswerable_returned_hits",
                    "retrieved_ids": [hit["id"] for hit in ranking],
                }
            ]
            if ranking
            else []
        )
        return {
            "answerable": False,
            "ranking": ranking,
            "recall_at_k": None,
            "reciprocal_rank_at_k": None,
            "ndcg_at_k": None,
            "failures": failures,
        }

    retrieved_ids = [hit["id"] for hit in ranking]
    relevant_ids = set(relevant)
    hits = [doc_id for doc_id in retrieved_ids if doc_id in relevant_ids]
    recall = len(hits) / len(relevant_ids)
    reciprocal_rank = next(
        (
            1.0 / position
            for position, doc_id in enumerate(retrieved_ids, start=1)
            if doc_id in relevant_ids
        ),
        0.0,
    )
    dcg = math.fsum(
        (2 ** relevant[doc_id] - 1) / math.log2(position + 1)
        for position, doc_id in enumerate(retrieved_ids, start=1)
        if doc_id in relevant_ids
    )
    ideal_grades = sorted(relevant.values(), reverse=True)[:k]
    ideal_dcg = math.fsum(
        (2**grade - 1) / math.log2(position + 1)
        for position, grade in enumerate(ideal_grades, start=1)
    )
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0
    missing = sorted(relevant_ids - set(hits))
    failures = [{"code": "missed_relevant", "missing_ids": missing}] if missing else []
    return {
        "answerable": True,
        "ranking": ranking,
        "recall_at_k": _clean_metric(recall),
        "reciprocal_rank_at_k": _clean_metric(reciprocal_rank),
        "ndcg_at_k": _clean_metric(ndcg),
        "failures": failures,
    }


def _clean_metric(value: float) -> float:
    return round(value, 12)


def _mean(values: list[float]) -> float | None:
    return _clean_metric(math.fsum(values) / len(values)) if values else None


def evaluate(documents: Sequence[dict], cases: Sequence[dict], *, k: int = 3) -> dict:
    """Evaluate both rankers with graded labels and separate no-answer reporting."""
    _validate_k(k)
    docs = _documents(documents)
    known_ids = {doc["id"] for doc in docs}
    checked_cases = _validate_cases(cases, known_ids)
    canonical_cases = [
        {
            "id": case["id"],
            "query": case["query"],
            "relevant": dict(sorted(case["relevant"].items())),
        }
        for case in checked_cases
    ]
    corpus_hash = _json_hash(docs)
    cases_hash = _json_hash(canonical_cases)
    policy = json.loads(json.dumps(RANKING_POLICY, sort_keys=True, allow_nan=False))
    answerable_cases = [case for case in checked_cases if case["relevant"]]
    unanswerable_cases = [case for case in checked_cases if not case["relevant"]]

    queries: list[dict] = []
    by_method: dict[str, list[dict]] = {method: [] for method in _METHODS}
    for case in checked_cases:
        query_result: dict = {
            "id": case["id"],
            "query": case["query"],
            "answerable": bool(case["relevant"]),
            "relevant": dict(sorted(case["relevant"].items())),
        }
        for method in _METHODS:
            raw_ranking = rank(docs, case["query"], method=method, k=k)
            ranking = _deduplicate_ranking(raw_ranking, known_ids, k)
            metrics = _case_metrics(ranking, case["relevant"], k)
            by_method[method].append(metrics)
            query_result[method] = metrics
        queries.append(query_result)

    method_reports: dict[str, dict] = {}
    for method in _METHODS:
        per_query = by_method[method]
        answered_metrics = [item for item in per_query if item["answerable"]]
        unanswered_metrics = [item for item in per_query if not item["answerable"]]
        method_reports[method] = {
            "macro_recall_at_k": _mean([item["recall_at_k"] for item in answered_metrics]),
            "mrr_at_k": _mean([item["reciprocal_rank_at_k"] for item in answered_metrics]),
            "ndcg_at_k": _mean([item["ndcg_at_k"] for item in answered_metrics]),
            "empty_result_rate": _mean(
                [1.0 if not item["ranking"] else 0.0 for item in unanswered_metrics]
            ),
            "false_positive_count": sum(bool(item["ranking"]) for item in unanswered_metrics),
            "per_query": [
                {
                    key: item[key]
                    for key in (
                        "answerable",
                        "recall_at_k",
                        "reciprocal_rank_at_k",
                        "ndcg_at_k",
                        "failures",
                    )
                }
                for item in per_query
            ],
        }

    return {
        "corpus_sha256": corpus_hash,
        "cases_sha256": cases_hash,
        "ranking_policy": policy,
        "k": k,
        "case_count": len(checked_cases),
        "answerable_count": len(answerable_cases),
        "unanswerable_count": len(unanswerable_cases),
        "methods": method_reports,
        "queries": queries,
        "unanswerables": [query for query in queries if not query["answerable"]],
    }
