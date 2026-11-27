"""Every query file is one statement that Relate's own safe mode accepts."""
import json
import re
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
PARAMS = {"on": "2026-03-01", "d": "2026-03-01", "value": 0.07, "rows": []}  # anything else gets a string


@pytest.mark.skipif(RELATE is None, reason="relate CLI not installed")
@pytest.mark.parametrize("name", READS)
def test_cli_safe_mode_accepts_read_queries(name, law_pack):
    path, _ = law_pack
    args = [RELATE, "--database", str(path), "--read-only", "--safe", "--json"]
    special = {"ask_vector.cypher": {"q": [0.01] * 256}}  # a 256-dimension vector, not a string
    for k in sorted(set(re.findall(r"\$(\w+)", (QUERY_DIR / name).read_text()))):
        args += ["--param", f"{k}={json.dumps(special.get(name, {}).get(k, PARAMS.get(k, 'x')))}"]
    cp = subprocess.run(args + [(QUERY_DIR / name).read_text()], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stdout[:400]


@pytest.mark.skipif(RELATE is None, reason="relate CLI not installed")
def test_readme_repeal_listing_matches_the_committed_pack():
    """README's 'Inspect them yourself' repeal table is real output of its query on data/ng-tax-2026.rl."""
    from inforce.paths import LAW_PACK, ROOT
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    query = re.search(r'"(MATCH \(i:Instrument\)-\[r:REPEALS\]->\(old\)[^"]*)"', readme).group(1)
    out = subprocess.run([RELATE, "--database", str(LAW_PACK), "--read-only", "--safe", "--mode", "table", query],
                         capture_output=True, text=True, check=True, encoding="utf-8").stdout
    ran = [ln for ln in out.splitlines() if ln.startswith("| ")]
    start = readme.index(ran[0])
    pasted = readme[start:].splitlines()[:len(ran) + 1]
    assert pasted[:len(ran)] == ran and not pasted[len(ran)].startswith("| ")
