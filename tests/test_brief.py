from inforce.brief import SECTIONS, brief, find_repo_root

from .test_scan import repo  # noqa: F401  (fixture)


def test_sections_in_fixed_order(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    b = brief(str(repo / "payroll" / "paye.py"), "2026-03-01", path, repo=repo)
    keys = [k for k in b if k in SECTIONS]
    assert keys == list(SECTIONS)


def test_file_brief_direct(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    b = brief(str(repo / "payroll" / "paye.py"), "2026-03-01", path, repo=repo)
    assert b["verdict"] == "STALE"
    assert {t["nowRef"] for t in b["truth"]} == {"ng.pit.band1.2026", "ng.pit.band2.2026", "ng.pit.rent_relief.2026"}
    assert [r["artifact"] for r in b["rests_on_it"]] == ["payroll/payslip.py::build_payslip", "tests/test_paye.py"]
    assert b["recheck"][0]["where"] == "payroll/paye.py:4"  # in line order
    assert b["recheck"][0]["action"] == "update"


def test_inherited_file_says_fix_upstream_first(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    b = brief(str(repo / "tests" / "test_paye.py"), "2026-03-01", path, repo=repo)
    assert b["verdict"] == "STALE"
    assert b["recheck"][0]["action"].startswith("fix first")
    assert b["recheck"][0]["artifact"].startswith("payroll/paye.py::")
    assert b["why"][0]["chain"][-1]["target"] == "tests/test_paye.py"


def test_question_brief_uses_check(law_pack):
    path, _ = law_pack
    b = brief("Is the CRA still 20% under PITA?", "2026-03-01", path)
    assert b["verdict"] == "STALE" and b["repo"] is None
    assert {t["nowRef"] for t in b["truth"]} == {"ng.pit.rent_relief.2026", "akn/ng/act/2025/7"}


def test_repo_root_found_from_inforce_dir(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    brief(str(repo / "payroll" / "paye.py"), "2026-03-01", path, repo=repo)  # creates .inforce/
    assert find_repo_root(repo / "payroll" / "paye.py") == repo
