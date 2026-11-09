"""Atomic corpus replacement and consistent read snapshots on separate connections."""

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from tracefind.models import content_hash, validate_documents

APPLICATION_ID = 0x54524644


class Conflict(Exception):
    """The supplied revision no longer describes the stored corpus."""


class Store:
    def __init__(self, path):
        if str(path) == ":memory:":
            raise ValueError("TraceFind requires a persistent database path")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                app_id = connection.execute("PRAGMA application_id").fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                tables = connection.execute("SELECT name FROM sqlite_master").fetchall()
                if (app_id, version) == (0, 0) and not tables:
                    connection.execute("""CREATE TABLE documents (
                        id TEXT PRIMARY KEY, title TEXT NOT NULL,
                        body TEXT NOT NULL, source TEXT NOT NULL)""")
                    connection.execute("""CREATE TABLE corpus (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        revision TEXT NOT NULL)""")
                    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                    connection.execute("PRAGMA user_version=1")
                elif (app_id, version) != (APPLICATION_ID, 1):
                    raise ValueError("Database is not a supported TraceFind database")
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def replace(self, documents: list[dict], expected_revision: str | None = None) -> dict:
        documents = validate_documents(documents)
        if expected_revision is not None and (
            not isinstance(expected_revision, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_revision)
        ):
            raise ValueError("Expected revision must be a lowercase SHA256")
        revision = content_hash(documents)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute("SELECT revision FROM corpus WHERE singleton=1").fetchone()
                current = row[0] if row else None
                if expected_revision is not None and expected_revision != current:
                    raise Conflict("Corpus revision changed; inspect it before retrying")
                changed = current != revision
                if changed:
                    connection.execute("DELETE FROM documents")
                    connection.executemany(
                        "INSERT INTO documents VALUES(?,?,?,?)",
                        [(d["id"], d["title"], d["body"], d["source"]) for d in documents],
                    )
                    connection.execute("INSERT OR REPLACE INTO corpus VALUES(1,?)", (revision,))
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        return {"revision": revision, "count": len(documents), "changed": changed}

    def snapshot(self) -> tuple[str | None, list[dict]]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            row = connection.execute("SELECT revision FROM corpus WHERE singleton=1").fetchone()
            documents = [
                dict(row) for row in connection.execute("SELECT * FROM documents ORDER BY id")
            ]
            connection.commit()
        return (row[0] if row else None), documents
