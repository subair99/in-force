from inforce.check import check_text
from inforce.paths import ROOT

STALE = ROOT / "demo" / "naira-payroll" / "answers" / "stale_answer.md"


def by_ref(result):
    return {i["ref"]: i for i in result["items"]}


def test_stale_answer_flags_paye_cra_and_cgt_with_successors(law_pack):
    """M1 done-when: old PAYE bands, CRA and company CGT flagged, each with its successor."""
    path, _ = law_pack
    r = check_text(STALE.read_text(), "2026-03-01", path)
    assert r["verdict"] == "STALE"
    items = by_ref(r)
    expect = {
        "ng.pit.band1.old": "ng.pit.band1.2026",
        "ng.pit.band2.old": "ng.pit.band2.2026",
        "ng.pit.cra.old": "ng.pit.rent_relief.2026",
        "ng.cgt.company.old": "ng.cgt.company.2026",
    }
    for old, new in expect.items():
        assert items[old]["verdict"] == "REPEALED", old
        assert items[old]["successorRef"] == new, old
        assert items[old]["endedOn"] == "2026-01-01"
        assert items[old]["path"][0] == f"Rule {old}"
    assert r["path"]  # proof for every stale item
    assert r["unverified"] is True
    assert "not legal or tax advice" in r["disclaimer"]


def test_same_answer_before_reform_is_not_stale(law_pack):
    path, _ = law_pack
    r = check_text(STALE.read_text(), "2025-06-01", path)
    assert r["verdict"] != "STALE"
    assert {i["verdict"] for i in r["items"]} == {"IN_FORCE"}


def test_new_law_answer_is_not_stale(law_pack):
    path, _ = law_pack
    text = ("Under the Nigeria Tax Act, the first NGN 800,000 is taxed at 0% and the next NGN 2,200,000 at 15%. "
            "Rent relief replaces the old allowance.")
    r = check_text(text, "2026-03-01", path)
    assert r["verdict"] == "SUSPECT"  # current law, but rules are still unverified
    assert all(i["verdict"] == "IN_FORCE" for i in r["items"])


def test_unknown_figure_is_not_recognised(law_pack):
    path, _ = law_pack
    r = check_text("the next ₦500,000 at 19%", "2026-03-01", path)
    [item] = r["items"]
    assert item["verdict"] == "NOT_RECOGNISED"
    assert r["verdict"] == "SUSPECT"


def test_amount_must_match_rule(law_pack):
    """15% exists as a 2026 band, but not for a first band of NGN 300,000."""
    path, _ = law_pack
    [item] = check_text("the first ₦300,000 at 15%", "2026-03-01", path)["items"]
    assert item["verdict"] == "NOT_RECOGNISED"


def test_no_claims(law_pack):
    path, _ = law_pack
    assert check_text("Nothing to see here.", "2026-03-01", path)["verdict"] == "NO_CLAIMS"
