"""Verify the checked-in evaluation without silently replacing its evidence."""

import math
from pathlib import Path

from tracefind.evaluation import evaluate
from tracefind.models import read_json, validate_documents

ROOT = Path(__file__).resolve().parents[1]


def compare(expected, actual, path="report"):
    if isinstance(expected, float) and isinstance(actual, (float, int)):
        if not math.isclose(expected, actual, rel_tol=0, abs_tol=1e-12):
            raise AssertionError(f"Numeric evaluation changed at {path}: {expected} -> {actual}")
    elif isinstance(expected, dict) and isinstance(actual, dict):
        assert expected.keys() == actual.keys(), f"Report fields changed at {path}"
        for key in expected:
            compare(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list) and isinstance(actual, list):
        assert len(expected) == len(actual), f"List length changed at {path}"
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            compare(left, right, f"{path}[{index}]")
    else:
        assert expected == actual, f"Evaluation changed at {path}"


def main():
    expected = read_json(ROOT / "docs/evaluation.json")
    actual = evaluate(
        validate_documents(read_json(ROOT / "data/corpus.json")),
        read_json(ROOT / "data/queries.json"),
        k=3,
    )
    compare(expected, actual)
    print("PASS: frozen evaluation reproduced (numeric tolerance 1e-12)")


if __name__ == "__main__":
    main()
