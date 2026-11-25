"""Open a Relate store for one command, run named queries, close it.

Facts this module relies on (checked by scripts/spike_relate.py, relate-db 1.3.0):
- A `.rl` file held by a writer cannot be opened again, not even read-only.
  The open fails with `relate.OperationalError("storage locked: ...")`
  (`retryable=False`; the CLI exits 5). We wait and retry, because our other
  opener is another short-lived InForce command.
- Connections are thread-affine. Open, use and close on one thread.
- `execute()` takes exactly one statement. `BEGIN`/`ROLLBACK` as Cypher text
  is a syntax error from Python; transactions use `autocommit = False` and
  `rollback()` / `commit()`.
- The Python client has no safe mode (the CLI's `--safe` does). We enforce
  the LIMIT rule here so a query that works in Python also passes `--safe`.
"""
from __future__ import annotations

import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import relate

EXIT_LOCKED = 5
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.25  # seconds; doubles per attempt


class StoreLocked(RuntimeError):
    """The store stayed locked by another opener after all retries (exit code 5)."""

    exit_code = EXIT_LOCKED


class UnboundedQuery(ValueError):
    """A read query has no LIMIT. Relate's safe mode would refuse it."""


# ---------------------------------------------------------------------------
# Named queries: inforce/queries/<name>.cypher, one statement per file
# ---------------------------------------------------------------------------

@cache
def query_text(name: str) -> str:
    """Return the text of `inforce/queries/<name>.cypher`."""
    path = resources.files("inforce") / "queries" / f"{name}.cypher"
    return path.read_text(encoding="utf-8")


def split_statements(text: str) -> list[str]:
    """Split a multi-statement script (e.g. schema.cypher) on ';'.

    Whole-line `//` comments are dropped first. Only for our own DDL files,
    which carry no ';' inside strings.
    """
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))
    return [s.strip() for s in body.split(";") if s.strip()]


# ---------------------------------------------------------------------------
# LIMIT guard
# ---------------------------------------------------------------------------

_STRINGS = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`")
_COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_WRITE = re.compile(r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|ALTER|FOREACH)\b", re.IGNORECASE)
_READ = re.compile(r"\bMATCH\b", re.IGNORECASE)  # safe mode refuses `MATCH … RETURN/WITH` without LIMIT
_LIMIT = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_ADMIN = re.compile(r"^\s*(SHOW|EXPLAIN|CALL\s+db\.)", re.IGNORECASE)


def _strip(text: str) -> str:
    return _STRINGS.sub("''", _COMMENTS.sub(" ", text))


def is_read(text: str) -> bool:
    code = _strip(text)
    return bool(_READ.search(code)) and not _WRITE.search(code) and not _ADMIN.match(code)


def check_bounded(text: str) -> None:
    """Raise UnboundedQuery if a read statement has no LIMIT.

    The rule (CLAUDE.md): every read query has a LIMIT. We require it even on
    pure aggregates so there is one rule to remember.
    """
    if is_read(text) and not _LIMIT.search(_strip(text)):
        first = " ".join(text.split())[:80]
        raise UnboundedQuery(f"read query without LIMIT: {first}...")


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def _is_lock_error(exc: BaseException) -> bool:
    return isinstance(exc, relate.OperationalError) and "storage locked" in str(exc)


class Store:
    """One open Relate connection. Create it with `open_store`, never directly."""

    def __init__(self, conn: relate.Connection, path: str, read_only: bool) -> None:
        self.conn = conn
        self.path = path
        self.read_only = read_only

    def execute(self, text: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run one statement (after the LIMIT guard) and return plain dict rows."""
        check_bounded(text)
        cur = self.conn.execute(text, params or {})
        return [dict(row) for row in cur.fetchall()]

    def run(self, name: str, **params: Any) -> list[dict[str, Any]]:
        """Run the named query file `inforce/queries/<name>.cypher`."""
        return self.execute(query_text(name), params)

    def run_script(self, name: str) -> int:
        """Run every statement of a multi-statement query file. Returns the count."""
        stmts = split_statements(query_text(name))
        for s in stmts:
            self.execute(s)
        return len(stmts)

    @contextmanager
    def rollback_only(self) -> Iterator[Store]:
        """Run statements in a transaction that is always rolled back (for `whatif`)."""
        self.conn.autocommit = False
        try:
            yield self
        finally:
            self.conn.rollback()
            self.conn.autocommit = True

    @contextmanager
    def transaction(self) -> Iterator[Store]:
        """Commit on success, roll back on any exception."""
        self.conn.autocommit = False
        try:
            yield self
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()
        finally:
            self.conn.autocommit = True


@contextmanager
def open_store(
    path: str | Path,
    read_only: bool = False,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    log=None,
) -> Iterator[Store]:
    """Open `path`, yield a Store, always close it.

    Retries a locked store `retries` times with doubling backoff, then raises
    StoreLocked. Any other open error is raised at once. `log`, if given, is
    called with a message on each retry (the two-writer demo shows these).
    """
    path = str(path)
    attempt = 0
    while True:
        try:
            conn = relate.connect(database=path, read_only=read_only)
            break
        except relate.OperationalError as exc:
            if not _is_lock_error(exc):
                raise
            if attempt >= retries:
                raise StoreLocked(f"{path} is locked by another process (tried {attempt + 1} times)") from exc
            delay = backoff * (2 ** attempt)
            if log:
                log(f"store locked, retry {attempt + 1}/{retries} in {delay:.2f}s: {path}")
            time.sleep(delay)
            attempt += 1
    try:
        yield Store(conn, path, read_only)
    finally:
        conn.close()
