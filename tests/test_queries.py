"""Every query file is one statement that Relate's own safe mode accepts."""
import json
import shutil
import subprocess
from importlib import resources

import pytest

from inforce.store import check_bounded, is_read, split_statements

QUERY_DIR = resources.files("inforce") / "queries"
FILES = sorted(p.name for p in QUERY_DIR.iterdir() if p.name.endswith(".cypher"))
SCRIPTS = {"schema.cypher"}  # multi-statement DDL, split by the loader
RELATE = shutil.which("relate")


@pytest.mark.parametrize("name", FILES)
def test_one_statement_and_bounded(name):
    text = (QUERY_DIR / name).read_text()
    stmts = split_statements(text)
    if name not in SCRIPTS:
        assert len(stmts) == 1, name
    for s in stmts:
        check_bounded(s)


READS = [n for n in FILES if n not in SCRIPTS and is_read((QUERY_DIR / n).read_text())]
PARAMS = {"on": "2026-03-01", "akn": "x", "repealed": "x"}


@pytest.mark.skipif(RELATE is None, reason="relate CLI not installed")
@pytest.mark.parametrize("name", READS)
def test_cli_safe_mode_accepts_read_queries(name, law_pack):
    path, _ = law_pack
    args = [RELATE, "--database", str(path), "--read-only", "--safe", "--json"]
    for k, v in PARAMS.items():
        if f"${k}" in (QUERY_DIR / name).read_text():
            args += ["--param", f"{k}={json.dumps(v)}"]
    cp = subprocess.run(args + [(QUERY_DIR / name).read_text()], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stdout[:400]
