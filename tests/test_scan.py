import shutil

import pytest
import relate

from inforce import scan as scan_mod
from inforce.scan import (
    evaluate,
    find,
    law_closure,
    load_paye_patterns,
    match_constant,
    scan,
)
from inforce.store import open_store

from .conftest import ROOT

DEMO = ROOT / "demo" / "naira-payroll"

DIRECT = {
    "payroll/paye.py::PIT_BANDS_2025", "payroll/paye.py::CRA_RATE", "payroll/paye.py::CRA_FLAT_MIN",
    "payroll/company_tax.py::CGT_RATE", "docs/hr-policy.md", "templates/payslip.html", "answers/stale_answer.md",
}
INHERITED = {
    "payroll/paye.py::consolidated_relief", "payroll/paye.py::compute_paye", "payroll/payslip.py::build_payslip",
    "payroll/company_tax.py::capital_gains_tax", "tests/test_paye.py", "tests/test_company_tax.py",
}


@pytest.fixture
def repo(tmp_path):
    dst = tmp_path / "naira-payroll"
    shutil.copytree(DEMO, dst, ignore=shutil.ignore_patterns(".inforce", "__pycache__", ".pytest_cache"))
    return dst


def by_id(report):
    return {a["id"]: a for a in report["artifacts"]}


# --- pattern matching -------------------------------------------------------

@pytest.mark.parametrize("name,value,rules", [
    ("PIT_BANDS_2025", ((300_000, 0.07), (300_000, 0.11)), {"ng.pit.band1.old", "ng.pit.band2.old"}),
    ("PIT_BANDS", ((800_000, 0.0), (2_200_000, 0.15)), {"ng.pit.band1.2026", "ng.pit.band2.2026"}),
    ("PIT_BANDS", ((500_000, 0.07),), set()),        # name matches, values don't
    ("CRA_RATE", 0.2, {"ng.pit.cra.old"}),
    ("CGT_RATE", 0.10, {"ng.cgt.company.old"}),
    ("CGT_RATE", 0.12, set()),
    ("SCRATCH", 0.07, set()),
])
def test_match_constant(name, value, rules):
    assert {h["rule"] for h in match_constant(name, value, load_paye_patterns())} == rules


# --- findings ---------------------------------------------------------------

def test_findings_on_demo():
    f = find(DEMO)
    assert {(e["artifact"], e["rule"]) for e in f.encodes} == {
        ("payroll/paye.py::PIT_BANDS_2025", "ng.pit.band1.old"),
        ("payroll/paye.py::PIT_BANDS_2025", "ng.pit.band2.old"),
        ("payroll/paye.py::CRA_RATE", "ng.pit.cra.old"),
        ("payroll/paye.py::CRA_FLAT_MIN", "ng.pit.cra.old"),
        ("payroll/company_tax.py::CGT_RATE", "ng.cgt.company.old"),
    }
    # (X)-[:USED_BY]->(Y): X is used by Y. (X)-[:TESTED_BY]->(T): X is tested by T.
    assert ("payroll/paye.py::CRA_RATE", "payroll/paye.py::consolidated_relief", "USED_BY") in f.edges
    assert ("payroll/paye.py::compute_paye", "payroll/payslip.py::build_payslip", "USED_BY") in f.edges
    assert ("payroll/paye.py::compute_paye", "tests/test_paye.py", "TESTED_BY") in f.edges
    assert "README.md" not in f.artifacts


def test_law_closure_follows_only_what_status_needs():
    rels = [
        {"type": "SETS", "s": "p1", "t": "r1"}, {"type": "CONTAINS", "s": "act", "t": "p1"},
        {"type": "REPEALS", "s": "new", "t": "act"}, {"type": "REPEALS", "s": "new", "t": "other"},
        {"type": "REPLACED_BY", "s": "r1", "t": "r2"}, {"type": "SETS", "s": "p2", "t": "r2"},
        {"type": "CONTAINS", "s": "new", "t": "p2"}, {"type": "CONTAINS", "s": "new", "t": "p3"},
    ]
    assert law_closure({"r1"}, rels) == {"r1", "p1", "act", "new", "r2", "p2"}


# --- full scan --------------------------------------------------------------

def test_scan_demo_flags_expected_artifacts(repo, law_pack):
    """M2 done-when: the expected stale artifacts, and .inforce/project.rl written."""
    path, _ = law_pack
    r = scan(repo, "2026-03-01", path)
    arts = by_id(r)
    assert r["verdict"] == "STALE"
    assert {a for a, x in arts.items() if x["status"] == "STALE" and not x["via"]} == DIRECT
    assert {a for a, x in arts.items() if x["status"] == "STALE" and x["via"]} == INHERITED
    assert (repo / ".inforce" / "project.rl").is_file()
    bands = arts["payroll/paye.py::PIT_BANDS_2025"]
    assert {b["successorRef"] for b in bands["because"]} == {"akn/ng/act/2025/7/sec_58"}
    assert all(len(b["scale"]) == 6 for b in bands["because"])
    assert "tests/test_paye.py" in arts["payroll/paye.py::CRA_RATE"]["alsoCheck"]


def test_inheritance_chain_explains_why(repo, law_pack):
    path, _ = law_pack
    arts = by_id(scan(repo, "2026-03-01", path))
    chain = arts["tests/test_paye.py"]["chain"]
    assert chain[0]["source"] in DIRECT
    assert chain[-1] == {"source": "payroll/paye.py::compute_paye", "type": "TESTED_BY",
                         "target": "tests/test_paye.py"}


def test_before_reform_nothing_is_stale(repo, law_pack):
    path, _ = law_pack
    r = scan(repo, "2025-06-01", path)
    assert not [a for a in r["artifacts"] if a["status"] == "STALE"]


def test_status_recomputed_from_date_on_read(repo, law_pack):
    """The committed graph caches status, but evaluate() recomputes it for any date, read-only."""
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    with open_store(repo / ".inforce" / "project.rl", read_only=True) as s:
        assert evaluate(s, "2026-03-01")["verdict"] == "STALE"
        assert evaluate(s, "2025-06-01")["verdict"] != "STALE"
        cached = s.execute("MATCH (a:Artifact {id: 'payroll/paye.py::CRA_RATE'}) "
                           "RETURN a.status AS st, a.statusOn AS on LIMIT 1")[0]
    assert cached["st"] == "STALE" and cached["on"].isoformat() == "2026-03-01"


def test_rescan_is_stable_and_keeps_other_writers_data(repo, law_pack):
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    store = repo / ".inforce" / "project.rl"
    conn = relate.connect(database=str(store))
    conn.execute("CREATE (:Artifact {id: 'agent/answer-1', kind: 'answer', origin: 'agent'})")
    conn.close()
    count = "MATCH (n) RETURN count(n) AS n LIMIT 1"
    with open_store(store, read_only=True) as s:
        before = s.execute(count)[0]["n"]
    scan(repo, "2026-03-01", path)
    with open_store(store, read_only=True) as s:
        assert s.execute(count)[0]["n"] == before
        assert s.execute("MATCH (a:Artifact {id: 'agent/answer-1'}) RETURN count(a) AS n LIMIT 1")[0]["n"] == 1


def test_project_graph_holds_only_the_law_it_needs(repo, law_pack):
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    with open_store(repo / ".inforce" / "project.rl", read_only=True) as s:
        shorts = {r["s"] for r in s.execute("MATCH (i:Instrument) RETURN i.short AS s LIMIT 50")}
        dated = s.execute("MATCH ()-[r:REPEALS]->() RETURN count(r) AS n, count(r.on) AS d LIMIT 1")[0]
    assert {"PITA", "CGTA", "NTA"} <= shorts
    assert "VAT Act" not in shorts and "IDITRA" not in shorts
    assert dated["n"] == dated["d"] > 0


FIXED_PAYE = '''
PIT_BANDS = ((800_000, 0.0), (2_200_000, 0.15))
RENT_RELIEF_CAP = 500_000


def compute_paye(gross):
    return 0.0
'''


def test_fixed_repo_has_no_stale(repo, law_pack):
    """What the agent fix in M3 must achieve: zero STALE."""
    path, _ = law_pack
    (repo / "payroll" / "paye.py").write_text(FIXED_PAYE)
    (repo / "payroll" / "company_tax.py").write_text("CIT_RATE = 0.30\n\n\ndef capital_gains_tax(gain):\n"
                                                    "    return round(gain * CIT_RATE, 2)\n")
    (repo / "docs" / "hr-policy.md").write_text("PAYE is deducted under the Nigeria Tax Act. Rent relief applies.\n")
    (repo / "templates" / "payslip.html").write_text("<footer>Tax computed under the Nigeria Tax Act.</footer>\n")
    (repo / "answers" / "stale_answer.md").unlink()
    r = scan(repo, "2026-03-01", path)
    assert [a["id"] for a in r["artifacts"] if a["status"] == "STALE"] == []
    arts = by_id(r)
    assert arts["payroll/paye.py::PIT_BANDS"]["status"] == "CURRENT"  # new law, verified against the Act


def test_scan_cli_exit_code(repo, law_pack):
    from typer.testing import CliRunner

    from inforce.cli import app
    path, _ = law_pack
    res = CliRunner().invoke(app, ["scan", str(repo), "--on", "2026-03-01", "--law", str(path)])
    assert res.exit_code == 3, res.output
    assert "ALSO CHECK" in res.output and "not legal or tax advice" in res.output


def test_module_exports():
    assert scan_mod.FOLLOW_IN and scan_mod.FOLLOW_OUT


def test_rescan_drops_links_withdrawn_from_the_law_pack(repo, law_pack):
    """Law copies are refreshed: a REPLACED_BY removed from the pack must not survive in project.rl."""
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    store = repo / ".inforce" / "project.rl"
    conn = relate.connect(database=str(store))  # simulate a link left behind by an older law pack
    conn.execute("MATCH (a:Rule {id: 'ng.pit.cra.old'}), (b:Rule {id: 'ng.pit.rent_relief.2026'}) "
                 "MERGE (a)-[:REPLACED_BY]->(b)")
    conn.close()
    arts = by_id(scan(repo, "2026-03-01", path))
    [cra] = arts["payroll/paye.py::CRA_RATE"]["because"]
    assert cra["successorRef"] is None
    assert [x["id"] for x in cra["related"]] == ["ng.pit.rent_relief.2026"]


def test_project_graph_holds_the_whole_new_scale(repo, law_pack):
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    with open_store(repo / ".inforce" / "project.rl", read_only=True) as s:
        ids = {r["id"] for r in s.execute("MATCH (p:Provision {akn: 'akn/ng/act/2025/7/sec_58'})-[:SETS]->(r:Rule) "
                                          "RETURN r.id AS id LIMIT 20")}
    assert {"ng.pit.band3.2026", "ng.pit.band4.2026", "ng.pit.band5.2026", "ng.pit.top.2026"} <= ids
