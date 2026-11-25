"""Day-1 spike: check every Relate feature InForce depends on.

Run:  python scripts/spike_relate.py
Then copy the printed report into docs/SPIKE_RESULTS.md and fix the spec
wherever a check FAILS. Nothing here is product code.

The API calls follow https://relatedb.ai/docs/reference/api/python.md
(relate-db 1.2.0). If an import or method fails, read `relate agent-context`
and the docs, then adjust this script - do not guess.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

import relate  # pip install relate-db

QUERIES = Path(__file__).resolve().parent.parent / "inforce" / "queries"
RELATE_BIN = shutil.which("relate") or "relate"

RESULTS: list[tuple[str, str, str]] = []


def check(name: str):
    def deco(fn):
        def run(*a, **kw):
            try:
                detail = fn(*a, **kw)
                RESULTS.append((name, "PASS", str(detail or "")))
            except Exception as exc:  # noqa: BLE001 - spike wants every failure
                RESULTS.append((name, "FAIL", f"{type(exc).__name__}: {exc}"))
                traceback.print_exc()
        return run
    return deco


def q(conn, text, params=None):
    return conn.execute(text, params or {}).fetchall()


@check("open single-file store (.rl)")
def t_open(path):
    conn = relate.connect(database=path)
    conn.close()
    return os.path.exists(path)


@check("unique constraint + MERGE idempotent")
def t_merge(path):
    conn = relate.connect(database=path)
    q(conn, "CREATE CONSTRAINT prov_akn IF NOT EXISTS FOR (p:Provision) REQUIRE p.akn IS UNIQUE")
    for _ in range(2):
        q(conn, "MERGE (p:Provision {akn: $a}) SET p.summary = $s", {"a": "akn/x/1", "s": "demo"})
    n = q(conn, "MATCH (p:Provision {akn: 'akn/x/1'}) RETURN count(p) AS n")[0]["n"]
    conn.close()
    assert n == 1, n
    return f"count={n}"


@check("date() values and comparisons")
def t_dates(path):
    conn = relate.connect(database=path)
    q(conn, """MERGE (p:Provision {akn:'akn/old/1'})
               SET p.validFrom = date('2011-01-01'), p.validTo = date('2026-01-01')""")
    rows = q(conn, """MATCH (p:Provision {akn:'akn/old/1'})
                      RETURN p.validTo <= date($on) AS repealed LIMIT 1""", {"on": "2026-03-01"})
    conn.close()
    assert rows[0]["repealed"] is True
    return rows


@check("EXISTS { } subquery")
def t_exists(path):
    conn = relate.connect(database=path)
    q(conn, """MERGE (s:Provision {akn:'akn/saver/1'}) SET s.validFrom = date('2026-01-01')
               WITH s MATCH (p:Provision {akn:'akn/old/1'}) MERGE (s)-[:SAVES {until: date('2028-01-01')}]->(p)""")
    rows = q(conn, """MATCH (p:Provision {akn:'akn/old/1'})
                      RETURN EXISTS { MATCH (s:Provision)-[:SAVES]->(p) } AS saved LIMIT 1""")
    conn.close()
    return rows


@check("variable-length path + collect")
def t_varlen(path):
    conn = relate.connect(database=path)
    q(conn, """MERGE (a:Rule {id:'r1'}) MERGE (b:Rule {id:'r2'}) MERGE (c:Rule {id:'r3'})
               MERGE (a)-[:REPLACED_BY]->(b) MERGE (b)-[:REPLACED_BY]->(c)""")
    rows = q(conn, """MATCH (a:Rule {id:'r1'})-[:REPLACED_BY*1..3]->(n:Rule)
                      RETURN collect(n.id) AS chain LIMIT 1""")
    conn.close()
    return rows


@check("transaction rollback (whatif)")
def t_rollback(path):
    conn = relate.connect(database=path)
    before = q(conn, "MATCH (n) RETURN count(n) AS n")[0]["n"]
    # Docs: set autocommit False, then execute() opens a transaction.
    try:
        conn.autocommit = False
    except AttributeError:
        conn.close()
        conn = relate.connect(database=path, autocommit=False)  # try the other spelling
    q(conn, "CREATE (:Scratch {x: 1})")
    conn.rollback()
    conn.autocommit = True
    after = q(conn, "MATCH (n) RETURN count(n) AS n")[0]["n"]
    conn.close()
    assert before == after, (before, after)
    return f"before={before} after={after}"


@check("vector index + SEARCH with WITH-filter")
def t_vector(path):
    conn = relate.connect(database=path)
    q(conn, """CREATE VECTOR INDEX prov_vec IF NOT EXISTS
               FOR (p:Provision) ON (p.embedding) WITH [p.inForceNow]
               OPTIONS {indexConfig: {`vector.dimensions`: 3, `vector.similarity_function`: 'cosine'}}""")
    q(conn, "MATCH (p:Provision {akn:'akn/x/1'}) SET p.embedding = [0.1, 0.9, 0.1], p.inForceNow = true")
    q(conn, "MATCH (p:Provision {akn:'akn/old/1'}) SET p.embedding = [0.1, 0.8, 0.2], p.inForceNow = false")
    rows = q(conn, """MATCH (p:Provision)
                      SEARCH p IN (VECTOR INDEX prov_vec FOR [0.1, 0.9, 0.1] WHERE p.inForceNow = true LIMIT 5) SCORE AS score
                      RETURN p.akn AS akn, score ORDER BY score DESC LIMIT 5""")
    conn.close()
    assert all(r["akn"] != "akn/old/1" for r in rows), rows
    return rows


@check("full-text index + SEARCH")
def t_fulltext(path):
    conn = relate.connect(database=path)
    q(conn, "CREATE FULLTEXT INDEX prov_fts IF NOT EXISTS FOR (p:Provision) ON EACH [p.summary]")
    rows = q(conn, """MATCH (p:Provision)
                      SEARCH p IN (FULLTEXT INDEX prov_fts FOR 'demo' LIMIT 3) SCORE AS score
                      RETURN p.akn AS akn, score LIMIT 3""")
    conn.close()
    return rows


@check("second open while closed (no lock leak)")
def t_reopen(path):
    a = relate.connect(database=path, read_only=True)
    a.close()
    b = relate.connect(database=path)
    b.close()
    return "ok"


@check("dates round-trip as datetime.date; null params")
def t_date_types(path):
    import datetime
    conn = relate.connect(database=path)
    rows = q(conn, "RETURN date($s) AS d, date($n) AS dn, $py < date('2027-01-01') AS ok",
             {"s": "2026-01-01", "n": None, "py": datetime.date(2026, 1, 1)})
    conn.close()
    assert rows[0]["d"] == datetime.date(2026, 1, 1) and rows[0]["dn"] is None and rows[0]["ok"], rows
    return rows


@check("one statement per execute() (multi-statement is a syntax error)")
def t_single_statement(path):
    conn = relate.connect(database=path)
    try:
        q(conn, "RETURN 1 AS a; RETURN 2 AS b")
    except relate.ProgrammingError as exc:
        return f"rejected as expected: {str(exc).splitlines()[0]}"
    finally:
        conn.close()
    raise AssertionError("multi-statement string was accepted; the loader can stop splitting")


@check("BEGIN/ROLLBACK as Cypher text (Python)")
def t_begin_text(path):
    conn = relate.connect(database=path)
    try:
        q(conn, "BEGIN")
        q(conn, "ROLLBACK")
        return "accepted"
    except relate.ProgrammingError as exc:
        return f"not supported, use conn.autocommit=False + conn.rollback(): {str(exc).splitlines()[0]}"
    finally:
        conn.close()


@check("second open while a writer holds the .rl (lock error shape)")
def t_lock(path):
    w = relate.connect(database=path)
    try:
        relate.connect(database=path, read_only=True).close()
        detail = "read-only open beside a writer SUCCEEDED"
    except relate.OperationalError as exc:
        detail = (f"{type(exc).__name__}: {str(exc).split(':')[0]}; retryable={exc.retryable}")
        assert "storage locked" in str(exc), exc
    cli = subprocess.run([RELATE_BIN, "--database", path, "--read-only", "--json",
                          "MATCH (n) RETURN count(n) AS n LIMIT 1"], capture_output=True, text=True)
    w.close()
    assert cli.returncode == 5, cli.returncode
    return f"{detail}; CLI exit={cli.returncode}"


@check("connections are thread-affine")
def t_threads(path):
    import threading
    conn = relate.connect(database=path)
    out = {}

    def other():
        try:
            q(conn, "RETURN 1 AS x")
            out["r"] = "usable from another thread"
        except relate.ProgrammingError:
            out["r"] = "ProgrammingError from another thread (as documented)"
    th = threading.Thread(target=other)
    th.start()
    th.join()
    conn.close()
    return out["r"]


def _statements(text: str) -> list[str]:
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    return [s.strip() for s in body.split(";") if s.strip()]


@check("queries/schema.cypher applies (twice, idempotent)")
def t_schema(path):
    conn = relate.connect(database=path.replace(".rl", ".schema.rl"))  # fresh: IF NOT EXISTS skips equivalent indexes
    stmts = _statements((QUERIES / "schema.cypher").read_text())
    for _ in range(2):
        for s in stmts:
            q(conn, s)
    names = [r["name"] for r in q(conn, "SHOW INDEXES YIELD name RETURN name LIMIT 50")]
    conn.close()
    return f"{len(stmts)} statements; indexes={sorted(names)}"


FIXTURE = [
    # old law, repealed 2026-01-01; new law in force 2026-01-01; a saver for a grant
    "CREATE (old:Instrument {akn:'i/old'}), (nta:Instrument {akn:'i/nta'}),"
    " (po:Provision {akn:'p/old', validTo: date('2026-01-01')}),"
    " (pn:Provision {akn:'p/new', validFrom: date('2026-01-01')}),"
    " (ps:Provision {akn:'p/saver', validFrom: date('2026-01-01')}),"
    " (ro:Rule {id:'r/old', key:'r/old', text:'old band'}), (rn:Rule {id:'r/new', text:'new band'}),"
    " (g:Grant {id:'g/1', title:'pioneer'}),"
    " (a:Artifact {id:'paye.py::BANDS'}), (t:Artifact {id:'tests/test_paye.py'}),"
    " (old)-[:CONTAINS]->(po), (nta)-[:CONTAINS]->(pn), (nta)-[:CONTAINS]->(ps),"
    " (nta)-[:REPEALS {on: date('2026-01-01')}]->(old),"
    " (po)-[:SETS]->(ro), (pn)-[:SETS]->(rn), (ro)-[:REPLACED_BY]->(rn),"
    " (g)-[:GRANTED_UNDER]->(po), (ps)-[:SAVES]->(g),"
    " (a)-[:ENCODES]->(ro), (a)-[:TESTED_BY]->(t),"
    " (old)-[:FROM]->(:Source {url: 'u'})",
]

QUERY_CASES = {
    "status_on": ({"akn": "p/old", "on": "2026-03-01"}, lambda r: r[0]["status"] == "REPEALED"),
    "stale_artifacts": ({"stale": ["r/old"]}, lambda r: r and r[0]["artifact"] == "paye.py::BANDS"),
    "ripple": ({"ids": ["paye.py::BANDS"]}, lambda r: r and r[0]["alsoCheck"] == ["tests/test_paye.py"]),
    "fallout": ({"repealed": "i/old", "on": "2026-03-01"}, lambda r: r and r[0]["verdict"] == "SAVED"),
    "keystones": ({}, lambda r: r and r[0]["weight"] >= 1),
}


@check("every queries/*.cypher runs on a fixture (Python + CLI --safe)")
def t_query_files(path):
    fx = path.replace(".rl", ".fixture.rl")
    conn = relate.connect(database=fx)
    for s in FIXTURE:
        q(conn, s)
    out = []
    for name, (params, ok) in QUERY_CASES.items():
        rows = q(conn, (QUERIES / f"{name}.cypher").read_text(), params)
        assert ok(rows), (name, rows)
        out.append(f"{name}={len(rows)}row")
    conn.close()
    for name, (params, _) in QUERY_CASES.items():
        args = [RELATE_BIN, "--database", fx, "--read-only", "--safe", "--json"]
        for k, v in params.items():
            # --param values are parsed as JSON: a bare 2026-03-01 is a malformed number.
            args += ["--param", f"{k}={json.dumps(v)}"]
        cli = subprocess.run(args + [(QUERIES / f"{name}.cypher").read_text()], capture_output=True, text=True)
        assert cli.returncode == 0, (name, cli.stdout[:300])
    return ", ".join(out) + "; all accepted by --safe"


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="inforce-spike-")
    path = os.path.join(tmp, "spike.rl")
    for t in (t_open, t_merge, t_dates, t_exists, t_varlen, t_rollback, t_vector, t_fulltext, t_reopen,
              t_date_types, t_single_statement, t_begin_text, t_lock, t_threads, t_schema, t_query_files):
        t(path)
    print("\n# Relate spike results\n")
    print(f"relate module: {getattr(relate, '__version__', 'unknown')}\n")
    print("| Check | Result | Detail |\n|---|---|---|")
    for name, res, detail in RESULTS:
        print(f"| {name} | {res} | {detail[:160].replace('|', '/')} |")
    print("\nAlso run in a shell and paste the output:")
    print("  relate --version")
    print("  relate agent-context")
    print(f'  relate --database {path} --read-only --mode envelope "MATCH (n) RETURN count(n) AS n LIMIT 1"')
    shutil.rmtree(tmp, ignore_errors=True) if os.environ.get("SPIKE_CLEAN") else None


if __name__ == "__main__":
    main()
