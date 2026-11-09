"""Local corpus operator, search client, and reproducible evaluation commands."""

import argparse
import json
import sqlite3
import sys

import uvicorn

from tracefind.api import create_app, search_snapshot
from tracefind.evaluation import evaluate
from tracefind.models import read_json, validate_documents
from tracefind.store import Conflict, Store


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Versioned document search and relevance evaluation"
    )
    parser.add_argument("--db", default="tracefind.db")
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("load", help="Atomically replace the corpus from a JSON file")
    load.add_argument("file")
    load.add_argument("--expected-revision")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--method", choices=["bm25", "overlap"], default="bm25")
    search.add_argument("--k", type=int, default=5)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--corpus", required=True)
    evaluation.add_argument("--queries", required=True)
    evaluation.add_argument("--k", type=int, default=3)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        if args.command == "load":
            documents = validate_documents(read_json(args.file))
            result = Store(args.db).replace(documents, expected_revision=args.expected_revision)
        elif args.command == "search":
            result = search_snapshot(Store(args.db), args.query, args.method, args.k)
        elif args.command == "evaluate":
            documents = validate_documents(read_json(args.corpus))
            result = evaluate(documents, read_json(args.queries), k=args.k)
        else:
            if not 1 <= args.port <= 65535:
                raise ValueError("Port must be 1-65535")
            uvicorn.run(create_app(args.db), host=args.host, port=args.port, access_log=False)
            return 0
    except Conflict as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, RecursionError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
