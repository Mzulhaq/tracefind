"""Bounded, explicit input contracts shared by ingestion and evaluation."""

import hashlib
import json
import re
from pathlib import Path

MAX_JSON_BYTES = 2 * 1024 * 1024
FIELDS = {"id": 64, "title": 160, "body": 8000, "source": 200}


def validate_documents(documents: list[dict]) -> list[dict]:
    if not isinstance(documents, list) or not 1 <= len(documents) <= 500:
        raise ValueError("Corpus must contain 1-500 documents")
    seen = set()
    total = 0
    output = []
    for document in documents:
        if not isinstance(document, dict) or set(document) != set(FIELDS):
            raise ValueError("Each document needs exactly id, title, body, source")
        for field, limit in FIELDS.items():
            value = document[field]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{field} must be nonblank text with at most {limit} characters")
            try:
                value.encode("utf-8")
            except UnicodeError as error:
                raise ValueError(f"{field} must contain valid Unicode") from error
            total += len(value)
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", document["id"]):
            raise ValueError(
                "Document ID must use 1-64 ASCII letters, digits, dots, dashes, underscores"
            )
        if document["id"] in seen:
            raise ValueError("Document IDs must be unique")
        seen.add(document["id"])
        output.append(dict(document))
    if total > 1_000_000:
        raise ValueError("Corpus exceeds 1,000,000 field characters")
    return sorted(output, key=lambda document: document["id"])


def content_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _unique_object(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("JSON object contains a duplicate key")
        output[key] = value
    return output


def _invalid_constant(value):
    raise ValueError("JSON must not contain nonfinite numbers")


def read_json(path: str | Path):
    with Path(path).open("rb") as handle:
        data = handle.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON file exceeds 2 MiB")
    return json.loads(
        data.decode("utf-8-sig"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant
    )
