import pytest
import yaml

from inforce import loader
from inforce.store import open_store

from .conftest import RULES


def test_refuses_unverified_without_flag(tmp_path):
    with pytest.raises(loader.UnverifiedLaw) as ei:
        loader.load(RULES, tmp_path / "law.rl")
    assert ei.value.entries
    assert not (tmp_path / "law.rl").exists()


def test_missing_verified_counts_as_unverified():
    data = {"rules": [{"id": "a", "verified": True}, {"id": "b"}, {"id": "c", "verified": "yes"}]}
    assert loader.unverified_entries(data) == ["rule b", "rule c"]


def test_load_builds_graph(law_pack):
    path, report = law_pack
    assert report.counts["Rule"] >= 10
    assert report.counts["Instrument"] >= 2
    with open_store(path, read_only=True) as s:
        rels = {r["t"]: r["n"] for r in s.execute(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n LIMIT 20")}
    for t in ("CONTAINS", "SETS", "REPEALS", "REPLACED_BY", "SAVES", "FROM"):
        assert rels.get(t), t


def test_load_is_repeatable(law_pack, tmp_path):
    path, first = law_pack
    second = loader.load(RULES, path, allow_unverified=True)
    assert second.counts == first.counts


def test_rule_values_match_yaml_exactly(law_pack):
    """The loader must never change a value or a verified flag."""
    path, _ = law_pack
    src = {r["id"]: r for r in loader.read_yaml(RULES)["rules"]}
    with open_store(path, read_only=True) as s:
        rows = s.execute("MATCH (r:Rule) RETURN r.id AS id, r.value AS value, r.text AS text, "
                         "r.verified AS verified LIMIT 500")
    assert len(rows) == len(src)
    for row in rows:
        y = src[row["id"]]
        assert row["value"] == y.get("value")
        assert row["text"] == y.get("text")
        assert row["verified"] is (y.get("verified") is True)


def test_todo_dates_are_left_unset_not_guessed(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "x.yaml").write_text(yaml.safe_dump({
        "instruments": [{"akn": "i/1", "assentedOn": "TODO", "commencesOn": None, "verified": True}],
    }))
    report = loader.load(tmp_path / "rules", tmp_path / "x.rl")
    assert any("not a date" in w for w in report.warnings)
    with open_store(tmp_path / "x.rl", read_only=True) as s:
        row = s.execute("MATCH (i:Instrument) RETURN i.assentedOn AS a LIMIT 1")[0]
    assert row["a"] is None


def test_dangling_repeal_is_an_error(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "x.yaml").write_text(yaml.safe_dump({
        "instruments": [{"akn": "i/1", "verified": True}],
        "repeals": [{"by": "i/1", "target": "i/missing", "verified": True}],
    }))
    with pytest.raises(loader.BadReference):
        loader.load(tmp_path / "rules", tmp_path / "x.rl")


@pytest.mark.parametrize("akn,on,expected", [
    ("TODO/ng/act/pita/sec_bands", "2025-12-31", "IN_FORCE"),
    ("TODO/ng/act/pita/sec_bands", "2026-01-01", "REPEALED"),
    ("akn/ng/act/2025/7/sec_58", "2025-12-31", "NOT_YET"),
    ("akn/ng/act/2025/7/sec_58", "2026-01-01", "IN_FORCE"),
])
def test_status_on_loaded_pack(law_pack, akn, on, expected):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        assert s.run("status_on", akn=akn, on=on)[0]["status"] == expected


def test_on_key_is_not_a_yaml11_boolean(law_pack):
    """`on:` must stay a key (PyYAML would read it as True and drop every repeal date)."""
    path, _ = law_pack
    data = loader.read_yaml(RULES)
    assert all("on" in r for r in data["repeals"])
    assert all(r["verified"] is False for r in data["rules"])  # true/false still booleans
    with open_store(path, read_only=True) as s:
        rows = s.execute("MATCH ()-[r:REPEALS]->() RETURN count(r) AS n, count(r.on) AS dated LIMIT 1")
    assert rows[0]["n"] == rows[0]["dated"] > 0


def test_successions_and_related_loaded(law_pack):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        succ = s.execute("MATCH (o:Provision)-[x:SUCCEEDED_BY]->(n:Provision) "
                         "RETURN o.akn AS o, n.akn AS n, x.verified AS v LIMIT 10")
        rel = s.execute("MATCH (a:Rule)-[:RELATED]->(b:Rule) RETURN a.id AS a, b.id AS b LIMIT 10")
        repl = s.execute("MATCH (a:Rule)-[:REPLACED_BY]->(b:Rule) RETURN a.id AS a, b.id AS b LIMIT 10")
    assert succ == [{"o": "TODO/ng/act/pita/sec_bands", "n": "akn/ng/act/2025/7/sec_58", "v": False}]
    assert rel == [{"a": "ng.pit.cra.old", "b": "ng.pit.rent_relief.2026"}]
    assert repl == [{"a": "ng.cgt.company.old", "b": "ng.cgt.company.2026"}]  # no band-to-band, no CRA link


def test_dangling_succession_is_an_error(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "x.yaml").write_text(yaml.safe_dump({
        "instruments": [{"akn": "i/1", "verified": True}],
        "provisions": [{"akn": "p/1", "instrument": "i/1", "verified": True}],
        "successions": [{"old": "p/1", "new": "p/missing", "verified": True}],
    }))
    with pytest.raises(loader.BadReference):
        loader.load(tmp_path / "rules", tmp_path / "x.rl")


def test_load_skips_up_to_date_pack(law_pack):
    path, _ = law_pack
    before = path.read_bytes()
    again = loader.load(RULES, path, allow_unverified=True)
    assert again.skipped and again.counts["Rule"] > 0
    assert path.read_bytes() == before  # untouched, so a fresh clone stays clean after `make demo`
    forced = loader.load(RULES, path, allow_unverified=True, force=True)
    assert not forced.skipped


def test_load_rebuilds_when_yaml_changes(tmp_path):
    import shutil
    rules = tmp_path / "rules"
    shutil.copytree(RULES, rules)
    out = tmp_path / "law.rl"
    loader.load(rules, out, allow_unverified=True)
    (rules / "extra.yaml").write_text("sources:\n  - {id: x, url: https://example.test/x}\n")
    assert not loader.load(rules, out, allow_unverified=True).skipped


def test_up_to_date_pack_is_kept_on_a_machine_without_the_model(law_pack, monkeypatch):
    """A fresh clone offline must not rebuild (and strip embeddings from) the committed pack."""
    from inforce import embed
    path, first = law_pack
    if not first.embedded:
        pytest.skip("embedding model not available here")
    before = path.read_bytes()
    monkeypatch.setattr(embed, "embed", lambda texts: None)
    again = loader.load(RULES, path, allow_unverified=True)
    assert again.skipped and again.embedded == first.embedded
    assert path.read_bytes() == before


def test_verify_lists_every_law_entry_with_source_and_line():
    items = loader.verify_list(RULES)
    data = loader.read_yaml(RULES)
    assert len(items) == sum(len(data.get(s, [])) for s in loader.LAW_SECTIONS)
    assert all(i["where"].startswith("ng-tax-2026.yaml:") for i in items)
    assert not any(i["verified"] for i in items)  # nothing verified yet, and InForce never sets it
    band3 = next(i for i in items if i["entry"] == "ng.pit.band3.2026")
    assert band3["source"] == "https://www.nrs.gov.ng/uploads/NIGERIA_TAX_ACT_2025_ef6bb812a5.pdf"  # gazetted NTA
    assert band3["page"] == "A542" and band3["secondarySources"] == ["https://taxsummaries.pwc.com/nigeria/individual"]
    pita = next(i for i in items if i["kind"] == "repeal" and i["entry"].endswith("pita"))
    assert "target: TODO/ng/act/pita" in (RULES / "ng-tax-2026.yaml").read_text().splitlines()[
        int(pita["where"].split(":")[1]) - 1]


def test_readme_verification_status_is_generated_from_the_data():
    """The README must state the true verification count (regenerate with `inforce verify --update-docs README.md`)."""
    from inforce.paths import ROOT
    readme = (ROOT / "README.md").read_text()
    assert loader.update_status_block(readme, loader.verify_summary(RULES)) == readme
    assert "checked by hand" not in readme.lower() and "hand-built from the official" not in readme.lower()


def test_build_hash_ignores_line_endings(tmp_path):
    """git on Windows checks out CRLF; the same YAML must give the same hash (no rebuild)."""
    import shutil
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    shutil.copytree(RULES, lf)
    shutil.copytree(RULES, crlf)
    for f in lf.glob("*.yaml"):  # the checkout may already be CRLF (Windows): build both forms explicitly
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    for f in crlf.glob("*.yaml"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert loader.build_hash(lf) == loader.build_hash(crlf)



@pytest.mark.parametrize("short,commences", [("NTA", "2026-01-01"), ("NTAA", "2026-01-01"),
                                             ("NRS Act", "2025-06-26"), ("JRB Act", "2025-06-26")])
def test_reform_acts_commencement_recorded_unverified(law_pack, short, commences):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        r = s.execute("MATCH (i:Instrument {short: $s}) RETURN i.commencesOn AS c, i.verified AS v LIMIT 1",
                      {"s": short})[0]
    assert (r["c"].isoformat(), r["v"]) == (commences, False)




NTA_PDF = "https://www.nrs.gov.ng/uploads/NIGERIA_TAX_ACT_2025_ef6bb812a5.pdf"


@pytest.mark.parametrize("short,primary,secondary", [
    ("NTA", NTA_PDF, ["thecable-gazettes"]),
    ("NTAA", "https://gazettengr.com/wp-content/uploads/NIGERIA-TAX-ADMINISTRATION-ACT-2025.pdf", ["thecable-gazettes"]),
    ("NRS Act", "https://media.premiumtimesng.com/wp-content/files/2026/01/"
                "Approved-Copy-to-Print.-Nigeria-Revenue-Service-Establishment-Act-2025-1.pdf.pdf",
     ["thecable-gazettes", "kpmg-gaps-2026"]),
    ("JRB Act", "https://media.premiumtimesng.com/wp-content/files/2026/01/"
                "Approved-Copy-to-Print-Joint-Revenue-Board-of-Nigeria-Establishment-Act-2025-B.pdf",
     ["thecable-gazettes", "kpmg-gaps-2026"]),
])
def test_reform_act_sources(law_pack, short, primary, secondary):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        r = s.execute("MATCH (i:Instrument {short: $s}) OPTIONAL MATCH (i)-[:FROM]->(src:Source) "
                      "RETURN src.url AS url, i.secondarySource AS sec, i.verified AS v LIMIT 1", {"s": short})[0]
    assert (r["url"], r["sec"], r["v"]) == (primary, secondary, False)



def test_committed_law_pack_is_up_to_date():
    """The committed pack must match the YAML, loader and queries, or `make demo` rebuilds it and dirties
    the tree (fix: `inforce load --allow-unverified --force`, then `inforce export`)."""
    from inforce.paths import LAW_PACK
    meta = loader.pack_meta(LAW_PACK)
    assert meta is not None and meta["hash"] == loader.build_hash(RULES)
    assert meta["embedModel"]  # committed with embeddings, so an offline clone never rebuilds it


def _one(path, q, params=None):
    with open_store(path, read_only=True) as s:
        return s.execute(q, params or {})[0]


def test_rent_relief_is_nta_s30_2_a_vi_page_a417(law_pack):
    path, _ = law_pack
    p = _one(path, "MATCH (p:Provision)-[:SETS]->(:Rule {id: 'ng.pit.rent_relief.2026'}) "
                   "RETURN p.number AS n, p.page AS page LIMIT 1")
    r = _one(path, "MATCH (r:Rule {id: 'ng.pit.rent_relief.2026'})-[:FROM]->(s:Source) "
                   "RETURN r.page AS page, s.id AS src, r.secondarySource AS src2, r.verified AS v LIMIT 1")
    assert p == {"n": "30(2)(a)(vi)", "page": "A417"}
    assert r == {"page": "A417", "src": "nta-text", "src2": ["pwc-individual-dev"], "v": False}


def test_fourth_schedule_page_a542_on_s58_and_all_six_bands(law_pack):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        p = s.execute("MATCH (p:Provision {akn: 'akn/ng/act/2025/7/sec_58'}) RETURN p.page AS page LIMIT 1")[0]
        bands = s.execute("MATCH (r:Rule)-[:FROM]->(s:Source) WHERE r.id STARTS WITH 'ng.pit.' AND r.id ENDS WITH '.2026' "
                          "AND r.topic = 'pit_band' RETURN r.id AS id, r.page AS page, s.id AS src LIMIT 20")
    assert p["page"] == "A542"
    assert len(bands) == 6 and all((b["page"], b["src"]) == ("A542", "nta-text") for b in bands)


def test_company_rate_set_by_s27_1_and_s56_with_s27_1_primary(law_pack):
    from inforce import law
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        sets = {r["akn"]: r["sec"] for r in s.execute(
            "MATCH (p:Provision)-[x:SETS]->(:Rule {id: 'ng.cgt.company.2026'}) "
            "RETURN p.akn AS akn, x.secondary AS sec LIMIT 5")}
        page56 = s.execute("MATCH (p:Provision {akn: 'akn/ng/act/2025/7/sec_56'}) RETURN p.page AS page LIMIT 1")[0]
        info = law.rule_status(s, "ng.cgt.company.2026", "2026-03-01")
    assert sets == {"akn/ng/act/2025/7/sec_27_1": False, "akn/ng/act/2025/7/sec_56": True}
    assert page56["page"] == "A428"
    assert info["provision"] == "akn/ng/act/2025/7/sec_27_1"  # deterministic: the primary provision


def test_jrb_primary_source_and_ntaa_commencement_page(law_pack):
    path, _ = law_pack
    jrb = _one(path, "MATCH (i:Instrument {short: 'JRB Act'})-[:FROM]->(s:Source) RETURN s.url AS url, s.title AS t LIMIT 1")
    ntaa = _one(path, "MATCH (i:Instrument {short: 'NTAA'}) RETURN i.page AS page, i.note AS note, i.verified AS v LIMIT 1")
    assert jrb["url"].endswith("Approved-Copy-to-Print-Joint-Revenue-Board-of-Nigeria-Establishment-Act-2025-B.pdf")
    assert "Government Notice No. 25, Act No. 6" in jrb["t"]
    assert ntaa == {"page": "A265", "v": False,
                    "note": "gazetted bracket reportedly reads 26 Jun 2025 (text extraction, not yet visually confirmed)"}


def test_nothing_is_verified_yet():
    assert not [i for i in loader.verify_list(RULES) if i["verified"]]


# --- Two official editions of the NTA number some sections differently -------------------------

def _numbers(path, akn):
    with open_store(path, read_only=True) as s:
        return {r["v"]: (r["n"], r["page"]) for r in s.execute(
            "MATCH (p:Provision {akn: $a})-[n:NUMBERED_AS]->(v:Version) RETURN v.version AS v, n.number AS n, "
            "n.page AS page LIMIT 5", {"a": akn})}


@pytest.mark.parametrize("akn,gazetted,certified", [
    ("akn/ng/act/2025/7/sec_182_2", ("183(2)", "A492"), ("182(2)", None)),       # IDITRA saving
    ("akn/ng/act/2025/7/sec_195", ("196", "A502"), ("195", None)),               # the repeals
    ("akn/ng/act/2025/7/commencement", ("203", "A515"), ("long title (Commencement)", None)),
    ("akn/ng/act/2025/7/sec_56", ("56", "A428"), ("56", None)),                  # same in both
    ("akn/ng/act/2025/7/sec_58", ("58 + Fourth Schedule", "A542"), ("58 + Fourth Schedule", None)),
    ("TODO/ng/act/2025/7/sec_rent_relief", ("30(2)(a)(vi)", "A417"), ("30(2)(a)(vi)", "A416")),
    ("akn/ng/act/2025/7/sec_27_1", ("27(1)", None), ("27(1)", "A414")),
    ("akn/ng/act/2025/7/sec_155_4", ("156(5)", "A478"), ("155(4)", "A477–478")),   # different number AND content
])
def test_each_edition_returns_its_own_number(law_pack, akn, gazetted, certified):
    path, _ = law_pack
    assert _numbers(path, akn) == {"gazetted": gazetted, "certified": certified}


def test_default_display_is_certified_with_gazetted_note(law_pack):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        p = s.execute("MATCH (p:Provision {akn: 'akn/ng/act/2025/7/sec_182_2'}) "
                      "RETURN p.number AS n, p.numberNote AS note LIMIT 1")[0]
        reps = s.execute("MATCH (:Instrument {short: 'NTA'})-[r:REPEALS]->() RETURN r.section AS sec, "
                         "r.byProvision AS bp, r.source AS src, r.secondarySource AS src2 LIMIT 10")
        vat = s.execute("MATCH (p:Provision {akn: 'akn/ng/act/2025/7/sec_155_4'}) "
                        "RETURN p.number AS n, p.numberNote AS nn, p.note AS note LIMIT 1")[0]
        toc = s.execute("MATCH (:Provision {akn: 'akn/ng/act/2025/7/sec_27_1'})-[n:NUMBERED_AS]->(:Version {version: 'gazetted'}) "
                        "RETURN n.note AS note LIMIT 1")[0]
    assert p == {"n": "182(2)", "note": "s.183(2) in the gazetted text"}
    assert len(reps) == 5 and all((r["sec"], r["bp"], r["src"], r["src2"]) ==
                                  ("195", "akn/ng/act/2025/7/sec_195", "nta-certified", ["nta-text", "chambers-cit-2026"])
                                  for r in reps)
    assert (vat["n"], vat["nn"]) == ("155(4)", "s.156(5) in the gazetted text")
    assert "extra subsection (4) on zero-rated suppliers" in vat["note"] and "content differs" in vat["note"]
    assert toc["note"] == "s.27 read from the gazetted table of contents; subsection and page TODO"


def test_diff_shows_both_renumberings(law_pack):
    from typer.testing import CliRunner

    from inforce import law
    from inforce.cli import app
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        d = law.diff_known_on(s, "2025-12-31", "2026-01-07")
    moves = {(n["d1"]["number"], n["d2"]["number"]) for n in d["numbering"]}
    assert {("183(2)", "182(2)"), ("196", "195"), ("203", "long title (Commencement)"), ("156(5)", "155(4)")} == moves
    assert d["numberingUnchecked"] == []  # every NTA provision is now numbered in both editions
    assert all(n["d1"]["version"] == "gazetted" and n["d2"]["version"] == "certified" for n in d["numbering"])
    import json
    res = CliRunner().invoke(app, ["diff", "--known-on", "2025-12-31", "--known-on", "2026-01-07", "--json",
                                   "--law", str(path)])
    cli = {(n["d1"]["number"], n["d1"]["page"], n["d2"]["number"]) for n in json.loads(res.stdout)["numbering"]}
    assert {("183(2)", "A492", "182(2)"), ("196", "A502", "195")} <= cli


@pytest.mark.parametrize("cited,note", [("182(2)", None), ("183(2)", "s.183(2) is s.182(2) in the certified")])
def test_citation_by_either_editions_number_finds_the_saving(law_pack, cited, note):
    from inforce.check import check_text
    path, _ = law_pack
    [item] = check_text(f"Under section {cited} of the Nigeria Tax Act, pioneer certificates continue.",
                        "2026-03-01", path)["items"]
    assert item["ref"] == "akn/ng/act/2025/7/sec_182_2" and item["verdict"] == "IN_FORCE"
    assert (note is None and "certified (current)" not in (item["note"] or "")) or note in item["note"]


def test_nta_sources_per_edition():
    data = loader.read_yaml(RULES)
    srcs = {x["id"]: x for x in data["sources"]}
    assert srcs["nta-text"]["url"] == NTA_PDF
    assert srcs["nta-certified"]["url"] == "https://tat.gov.ng/NIGERIA-TAX-ADMINISTRATION-ACT-2025.pdf"
    assert "pp. A387–A596" in srcs["nta-certified"]["title"] and "Tax Appeal Tribunal" in srcs["nta-certified"]["title"]
    assert "content is the Nigeria Tax Act" in srcs["nta-certified"]["note"]
    versions = {v["version"]: v for v in next(i for i in data["instruments"] if i.get("short") == "NTA")["versions"]}
    assert versions["gazetted"]["source"] == "nta-text" and versions["certified"]["source"] == "nta-certified"
    nta = [p for p in data["provisions"] if p["instrument"] == "akn/ng/act/2025/7"]
    assert len(nta) == 8 and all(p["source"] in ("nta-text", "nta-certified") for p in nta)
    assert not any(p.get("verified") for p in nta)


def test_ntaa_commencement_in_long_title(law_pack):
    path, _ = law_pack
    r = _one(path, "MATCH (i:Instrument {short: 'NTAA'}) RETURN i.commencementSection AS sec, i.commencesOn AS c, "
                   "i.note AS note, i.page AS page LIMIT 1")
    assert (r["sec"], r["c"].isoformat(), r["page"]) == ("long title (Commencement)", "2026-01-01", "A265")
    assert r["note"] == "gazetted bracket reportedly reads 26 Jun 2025 (text extraction, not yet visually confirmed)"


def test_verify_sheet_shows_both_numberings(tmp_path):
    from inforce.verify_sheet import build_sheet
    text = build_sheet(RULES)
    repeal_rows = [ln for ln in text.splitlines() if ln.startswith("- [") and "**repeal**" in ln]
    assert len(repeal_rows) == 5 and all("under section 195 (s.196 in the gazetted text)" in r for r in repeal_rows)
    assert "### Section 182(2) (s.183(2) in the gazetted text)" in text
    assert "### Long title (Commencement) (s.203 in the gazetted text)" in text   # not "Section long title"
    assert "Section long title" not in text
    assert "### Section 155(4) (s.156(5) in the gazetted text)" in text
    assert 'gazetted text: "203" (p. A515) says "first day of January, 2026"' in text

