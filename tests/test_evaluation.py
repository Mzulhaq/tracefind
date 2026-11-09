from __future__ import annotations

import copy

import pytest

import tracefind.evaluation as evaluation
from tracefind.evaluation import evaluate

DOCS = [
    {"id": "a", "title": "Billing", "body": "billing refund billing", "source": "runbook-a"},
    {"id": "b", "title": "Billing", "body": "billing invoice", "source": "runbook-b"},
    {"id": "c", "title": "Account", "body": "login password", "source": "runbook-c"},
]
CASES = [
    {"id": "q1", "query": "billing", "relevant": {"a": 3, "b": 1}},
    {"id": "q2", "query": "refund", "relevant": {"a": 2, "c": 1}},
    {"id": "q3", "query": "dragonfruit", "relevant": {}},
    {"id": "q4", "query": "billing", "relevant": {}},
]


def test_evaluator_reports_hashes_policy_methods_queries_and_failures():
    report = evaluate(DOCS, CASES, k=2)
    assert report["k"] == 2
    assert len(report["corpus_sha256"]) == 64
    assert len(report["cases_sha256"]) == 64
    assert report["ranking_policy"]["tokenization"] == "NFKC + casefold + [^\\W_]+"
    assert report["case_count"] == 4
    assert report["answerable_count"] == 2
    assert report["unanswerable_count"] == 2
    assert [case["id"] for case in report["unanswerables"]] == ["q3", "q4"]
    for method in ("bm25", "overlap"):
        metrics = report["methods"][method]
        assert metrics["macro_recall_at_k"] == pytest.approx(0.75)
        assert metrics["mrr_at_k"] == pytest.approx(1.0)
        assert metrics["empty_result_rate"] == pytest.approx(0.5)
        assert metrics["false_positive_count"] == 1
        assert report["queries"][0][method]["ndcg_at_k"] == pytest.approx(1.0)
        assert report["queries"][1][method]["recall_at_k"] == pytest.approx(0.5)
        assert report["queries"][1][method]["ndcg_at_k"] == pytest.approx(
            3 / (3 + 1 / __import__("math").log2(3))
        )
        assert report["queries"][2][method]["answerable"] is False
        assert report["queries"][2][method]["failures"] == []
        assert report["queries"][3][method]["failures"][0]["code"] == "unanswerable_returned_hits"


def test_evaluator_output_is_json_safe_and_input_order_independent():
    baseline = evaluate(DOCS, CASES, k=3)
    reordered = evaluate(list(reversed(DOCS)), list(reversed(CASES)), k=3)
    assert baseline == reordered
    # JSON serialization must succeed without custom encoders or non-finite values.
    import json

    encoded = json.dumps(baseline, allow_nan=False, sort_keys=True)
    assert json.loads(encoded) == baseline


def test_all_unanswerable_suite_has_separate_empty_metrics_and_null_answer_metrics():
    report = evaluate(DOCS, [{"id": "none", "query": "zzzz", "relevant": {}}])
    for metrics in report["methods"].values():
        assert metrics["macro_recall_at_k"] is None
        assert metrics["mrr_at_k"] is None
        assert metrics["ndcg_at_k"] is None
        assert metrics["empty_result_rate"] == 1.0
        assert metrics["false_positive_count"] == 0


@pytest.mark.parametrize(
    "cases",
    [
        [],
        [{"id": "q", "query": "x", "relevant": {"missing": 1}}],
        [{"id": "q", "query": "x", "relevant": {"a": True}}],
        [{"id": "q", "query": "x", "relevant": {"a": 0}}],
        [{"id": "q", "query": "x", "relevant": {"a": 4}}],
        [{"id": "q", "query": "x", "relevant": {"a": 1.0}}],
        [{"id": "q", "query": "x", "relevant": {"a": "3"}}],
        [
            {"id": "same", "query": "x", "relevant": {}},
            {"id": "same", "query": "y", "relevant": {}},
        ],
        [{"id": "q", "query": "x", "relevant": {}, "extra": 1}],
        [{"id": "q", "query": "x", "relevant": []}],
    ],
)
def test_invalid_cases_or_labels_are_rejected(cases):
    with pytest.raises(ValueError):
        evaluate(DOCS, cases)


def test_invalid_k_and_duplicate_document_ids_are_rejected():
    with pytest.raises(ValueError):
        evaluate(DOCS, CASES, k=True)
    with pytest.raises(ValueError):
        evaluate(DOCS + [copy.deepcopy(DOCS[0])], CASES)


def test_duplicate_predictions_are_deduplicated_before_cutoff(monkeypatch):
    repeated = [{"id": "a", "score": 3.0}, {"id": "a", "score": 2.0}, {"id": "b", "score": 1.0}]
    monkeypatch.setattr(evaluation, "rank", lambda *_args, **_kwargs: repeated)
    report = evaluate(DOCS, [{"id": "q", "query": "billing", "relevant": {"a": 1, "b": 1}}], k=2)
    ranked = report["queries"][0]["bm25"]["ranking"]
    assert [hit["id"] for hit in ranked] == ["a", "b"]
    assert report["queries"][0]["bm25"]["recall_at_k"] == 1.0
