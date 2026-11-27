from inforce.check import check_text
from inforce.paths import ROOT

STALE = ROOT / "demo" / "naira-payroll" / "answers" / "stale_answer.md"


def by_ref(result):
    return {i["ref"]: i for i in result["items"]}


def test_stale_answer_flags_paye_cra_and_cgt_with_successors(law_pack):
    """M1 done-when: old PAYE bands, CRA and company CGT flagged, each with what (if anything) replaced it."""
    path, _ = law_pack
    r = check_text(STALE.read_text(), "2026-03-01", path)
    assert r["verdict"] == "STALE"
    items = by_ref(r)
    for old in ("ng.pit.band1.old", "ng.pit.band2.old", "ng.pit.cra.old", "ng.cgt.company.old"):
        assert items[old]["verdict"] == "REPEALED", old
        assert items[old]["endedOn"] == "2026-01-01"
        assert items[old]["path"][0] == f"Rule {old}"
    # PIT bands: replaced as a whole by the new scale (no band-to-band link)
    for old in ("ng.pit.band1.old", "ng.pit.band2.old"):
        assert items[old]["successorRef"] == "akn/ng/act/2025/7/sec_58"
        assert [x["id"] for x in items[old]["successorScale"]] == [
            "ng.pit.band1.2026", "ng.pit.band2.2026", "ng.pit.band3.2026", "ng.pit.band4.2026",
            "ng.pit.band5.2026", "ng.pit.top.2026"]
    # CRA: dropped, no successor; rent relief only related
    assert items["ng.pit.cra.old"]["successorRef"] is None
    assert "ended with no replacement" in items["ng.pit.cra.old"]["note"]
    assert [x["id"] for x in items["ng.pit.cra.old"]["related"]] == ["ng.pit.rent_relief.2026"]
    # company CGT: a true one-to-one successor
    assert items["ng.cgt.company.old"]["successorRef"] == "ng.cgt.company.2026"
    assert r["path"] and r["unverified"] is True
    assert "not legal or tax advice" in r["disclaimer"]


def test_new_middle_band_is_recognised(law_pack):
    path, _ = law_pack
    [i] = check_text("the next ₦9,000,000 at 18%", "2026-03-01", path)["items"]
    assert (i["ref"], i["verdict"]) == ("ng.pit.band3.2026", "IN_FORCE")


def test_same_rate_different_band_told_apart_by_amount(law_pack):
    path, _ = law_pack
    [new] = check_text("next ₦13,000,000 at 21%", "2026-03-01", path)["items"]
    [old] = check_text("next ₦1,600,000 at 21%", "2026-03-01", path)["items"]
    assert (new["ref"], new["verdict"]) == ("ng.pit.band4.2026", "IN_FORCE")
    assert (old["ref"], old["verdict"]) == ("ng.pit.band5.old", "REPEALED")


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
    assert r["verdict"] == "CURRENT"  # current law, and the NTA rules are now verified against the Act
    assert all(i["verdict"] == "IN_FORCE" for i in r["items"])


def test_unknown_figure_is_not_recognised(law_pack):
    path, _ = law_pack
    r = check_text("the next ₦500,000 at 17%", "2026-03-01", path)
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


def test_unknown_tax_act_is_not_recognised_not_no_claims(law_pack):
    """README: a claim that matches no rule is "not recognised", never guessed (and never NO_CLAIMS)."""
    path, _ = law_pack
    env = check_text("The Stamp Duties Act requires duty on receipts.", "2026-03-01", path)
    assert env["verdict"] == "SUSPECT"
    [item] = env["items"]
    assert (item["claim"], item["verdict"]) == ("Stamp Duties Act", "NOT_RECOGNISED")


def test_other_act_in_the_pack_resolves_by_title(law_pack):
    path, _ = law_pack
    [item] = check_text("Under the Nigeria Tax Administration Act.", "2026-03-01", path)["items"]
    assert (item["ref"], item["verdict"]) == ("TODO/ng/act/2025/ntaa", "IN_FORCE")


def test_source_title_explains_a_misleading_url(law_pack):
    """The certified NTA is hosted as '...ADMINISTRATION-ACT-2025.pdf': its title must travel with the URL."""
    path, _ = law_pack
    [item] = check_text("Under PITA.", "2026-03-01", path)["items"]
    assert "ADMINISTRATION" in item["source"]
    assert item["sourceTitle"].startswith("Nigeria Tax Act, 2025")


def test_verified_repeal_of_a_stub_act_is_verified(law_pack):
    """NTA s.195 repealing PITA is verified; the PITA stub is not. The REPEALED verdict rests on the repeal."""
    path, _ = law_pack
    [item] = check_text("Under PITA.", "2026-03-01", path)["items"]
    assert (item["verdict"], item["verified"]) == ("REPEALED", True)
    assert "repeal verified" in item["note"]
    # before the repeal, IN_FORCE rests on the stub's own entry, which is unverified
    [before] = check_text("Under PITA.", "2025-06-01", path)["items"]
    assert (before["verdict"], before["verified"]) == ("IN_FORCE", False)
    assert "Act not yet verified" in before["note"]


def test_readme_headline_example_matches_a_real_run(law_pack):
    """README's PITA example: the verdict column (with or without *) must be what `check` gives."""
    path, _ = law_pack
    env = check_text("Under PITA the first ₦300,000 is taxed at 7%.", "2026-11-25", path)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for item in env["items"]:
        mark = "REPEALED  " if item["verified"] else "REPEALED *"
        assert f"│ {item['claim'].ljust(29)} │ {mark} │" in readme, item["claim"]


def test_in_force_with_no_start_date_says_so(law_pack):
    """The old Acts have no commencement date in the pack: a 1990 check must not look certain."""
    from inforce.check import START_UNKNOWN
    path, _ = law_pack
    items = check_text("Under PITA the CRA applies.", "1990-01-01", path)["items"]
    assert [i["verdict"] for i in items] == ["IN_FORCE", "IN_FORCE"]
    assert all(START_UNKNOWN in i["note"] for i in items)
    # a known start date gives no such note (NTA commences 1 Jan 2026)
    [nta] = check_text("Under the Nigeria Tax Act.", "2026-03-01", path)["items"]
    assert START_UNKNOWN not in (nta["note"] or "")
