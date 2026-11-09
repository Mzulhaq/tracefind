from __future__ import annotations

import math
import unicodedata

import pytest

from tracefind.retrieval import rank, tokenize


def docs():
    return [
        {"id": "b", "title": "Apple", "body": "banana", "source": "guide-b"},
        {"id": "a", "title": "Apple", "body": "apple apple", "source": "guide-a"},
    ]


def test_tokenize_nfkc_casefold_and_split_nonword_or_underscore():
    assert tokenize("Straße ＡＢＣ foo_bar") == ["strasse", "abc", "foo", "bar"]
    assert tokenize("中文") == ["中文"]
    assert tokenize("!!!___") == []
    with pytest.raises(ValueError):
        tokenize(None)


def test_bm25_uses_unique_query_terms_positive_idf_and_fixed_parameters():
    result = rank(docs(), "APPLE apple", k=2)
    assert [item["id"] for item in result] == ["a", "b"]
    idf = math.log(1 + (2 - 2 + 0.5) / (2 + 0.5))
    avgdl = 2.5
    expected_a = idf * (3 * 2.2) / (3 + 1.2 * (1 - 0.75 + 0.75 * 3 / avgdl))
    expected_b = idf * 2.2 / (1 + 1.2 * (1 - 0.75 + 0.75 * 2 / avgdl))
    assert result[0]["score"] == pytest.approx(expected_a)
    assert result[1]["score"] == pytest.approx(expected_b)
    assert all(item["score"] > 0 and math.isfinite(item["score"]) for item in result)
    assert rank(docs(), "apple", k=2) == result


def test_overlap_counts_distinct_query_tokens():
    result = rank(docs(), "apple apple banana", method="overlap", k=2)
    assert result == [{"id": "b", "score": 2.0}, {"id": "a", "score": 1.0}]


def test_ties_and_corpus_order_are_deterministic():
    input_docs = [
        {"id": "z", "title": "same", "body": "term", "source": "z"},
        {"id": "a", "title": "same", "body": "term", "source": "a"},
    ]
    assert rank(input_docs, "term") == rank(list(reversed(input_docs)), "term")
    assert [item["id"] for item in rank(input_docs, "term")] == ["a", "z"]


@pytest.mark.parametrize("query", ["", "___!!!", "   "])
def test_empty_or_punctuation_only_query_has_no_hits(query):
    assert rank(docs(), query) == []


@pytest.mark.parametrize("k", [0, 21, True, 1.0, "2"])
def test_invalid_k_is_rejected(k):
    with pytest.raises(ValueError):
        rank(docs(), "apple", k=k)


def test_invalid_method_query_and_duplicate_ids_are_rejected():
    with pytest.raises(ValueError):
        rank(docs(), "apple", method="dense")
    with pytest.raises(ValueError):
        rank(docs(), "q" * 513)
    with pytest.raises(ValueError):
        rank(docs() + [docs()[0]], "apple")


@pytest.mark.parametrize(
    "bad_doc",
    [
        {"id": "bad/id", "title": "t", "body": "b", "source": "s"},
        {"id": "x", "title": "", "body": "b", "source": "s"},
        {"id": "x", "title": "t", "body": "b", "source": "s", "extra": "x"},
    ],
)
def test_invalid_documents_are_rejected(bad_doc):
    with pytest.raises(ValueError):
        rank([bad_doc], "query")


def test_character_limit_counts_ids_as_part_of_the_corpus():
    exact = [
        {
            "id": f"{'a' * 60}{index:04d}",
            "title": "t",
            "body": "x" * 7934,
            "source": "s",
        }
        for index in range(125)
    ]
    assert rank(exact, "missing") == []
    over = [dict(doc) for doc in exact]
    over[0]["body"] += "x"
    with pytest.raises(ValueError):
        rank(over, "missing")


def test_invalid_unicode_surrogate_in_document_is_rejected():
    bad = {"id": "a", "title": "\ud800", "body": "text", "source": "source"}
    with pytest.raises(ValueError):
        rank([bad], "text")


def test_tokenizer_is_nfkc_idempotent_for_fullwidth_text():
    text = "ＡＢＣ"
    assert tokenize(text) == tokenize(unicodedata.normalize("NFKC", text).casefold())
