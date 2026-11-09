import json
import subprocess
import sys

import pytest

from tests.test_store import doc
from tracefind.cli import main
from tracefind.models import read_json


def test_load_search_and_compare_and_swap(tmp_path, capsys):
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps([doc()]), encoding="utf-8")
    db = str(tmp_path / "search.db")
    assert main(["--db", db, "load", str(path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["--db", db, "load", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is False
    assert main(["--db", db, "search", "password"]) == 0
    assert json.loads(capsys.readouterr().out)["revision"] == first["revision"]
    assert main(["--db", db, "load", str(path), "--expected-revision", "0" * 64]) == 2
    assert "revision" in capsys.readouterr().err


def test_evaluate_command_returns_both_methods(tmp_path, capsys):
    corpus = tmp_path / "corpus.json"
    queries = tmp_path / "queries.json"
    corpus.write_text(json.dumps([doc()]), encoding="utf-8")
    queries.write_text(
        json.dumps([{"id": "q1", "query": "password", "relevant": {"reset": 3}}]), encoding="utf-8"
    )
    assert main(["evaluate", "--corpus", str(corpus), "--queries", str(queries)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert "bm25" in json.dumps(output) and "overlap" in json.dumps(output)


@pytest.mark.parametrize(
    "content",
    [
        '[{"id":"a","id":"b"}]',
        "[NaN]",
        "{}",
        '[{"id":"a","title":"x","body":"\\ud800","source":"x"}]',
        "x" * (2 * 1024 * 1024 + 1),
    ],
)
def test_invalid_load_fails_before_database_creation(tmp_path, capsys, content):
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    db = tmp_path / "unused.db"
    assert main(["--db", str(db), "load", str(path)]) == 1
    assert json.loads(capsys.readouterr().err)["error"]
    assert not db.exists()


def test_read_json_handles_utf8_bom(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b'\xef\xbb\xbf{"ok":true}')
    assert read_json(path) == {"ok": True}


def test_installed_module_help():
    result = subprocess.run(
        [sys.executable, "-m", "tracefind.cli", "--help"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "evaluate" in result.stdout
