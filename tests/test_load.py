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
    assert band3["source"] == "https://taxsummaries.pwc.com/nigeria/individual"
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


def test_nta_repeals_cite_section_196_in_the_gazette(law_pack):
    """Every NTA repeal records s.196 and the gazetted Act (p. A502), with Chambers kept as secondary."""
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        rows = s.execute("MATCH (:Instrument {short: 'NTA'})-[r:REPEALS]->(t) "
                         "RETURN t.short AS t, r.section AS sec, r.page AS page, r.source AS src, "
                         "r.secondarySource AS src2 LIMIT 20")
        cite = s.execute("MATCH (s:Source {id: 'nta-text'}) RETURN s.citation AS c LIMIT 1")[0]["c"]
    assert len(rows) == 5
    assert all((r["sec"], r["page"], r["src"], r["src2"]) == ("196", "A502", "nta-text", ["chambers-cit-2026"])
               for r in rows)
    assert "Gazette No. 117" in cite and "Act No. 7" in cite


@pytest.mark.parametrize("short,commences", [("NTA", "2026-01-01"), ("NTAA", "2026-01-01"),
                                             ("NRS Act", "2025-06-26"), ("JRB Act", "2025-06-26")])
def test_reform_acts_commencement_recorded_unverified(law_pack, short, commences):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        r = s.execute("MATCH (i:Instrument {short: $s}) RETURN i.commencesOn AS c, i.verified AS v LIMIT 1",
                      {"s": short})[0]
    assert (r["c"].isoformat(), r["v"]) == (commences, False)


def test_iditra_savings_clause_is_section_183_2(law_pack):
    """The gazetted NTA numbers the IDITRA savings clause s.183(2) (p. A492); 182(2) was wrong."""
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        saver = s.execute("MATCH (p:Provision)-[x:SAVES]->(:Grant) RETURN p.akn AS akn, p.number AS n, "
                          "p.page AS page, x.page AS xpage LIMIT 1")[0]
        old = s.execute("MATCH (p:Provision) WHERE p.number = '182(2)' OR p.akn ENDS WITH 'sec_182_2' "
                        "RETURN count(p) AS c LIMIT 1")[0]["c"]
    assert saver == {"akn": "akn/ng/act/2025/7/sec_183_2", "n": "183(2)", "page": "A492", "xpage": "A492"}
    assert old == 0


def test_verify_sheet_shows_repeal_section_and_gazette_citation(tmp_path):
    from inforce.verify_sheet import build_sheet
    text = build_sheet(RULES)
    rows = [ln for ln in text.splitlines() if ln.startswith("- [") and "**repeal**" in ln]
    assert len(rows) == 5
    assert all("under section 196" in r and "Gazette No. 117" in r and "p. A502" in r and "secondary" in r
               for r in rows)


NTA_PDF = "https://www.nrs.gov.ng/uploads/NIGERIA_TAX_ACT_2025_ef6bb812a5.pdf"


@pytest.mark.parametrize("short,primary,secondary", [
    ("NTA", NTA_PDF, ["thecable-gazettes"]),
    ("NTAA", "https://gazettengr.com/wp-content/uploads/NIGERIA-TAX-ADMINISTRATION-ACT-2025.pdf", ["thecable-gazettes"]),
    ("NRS Act", "https://media.premiumtimesng.com/wp-content/files/2026/01/"
                "Approved-Copy-to-Print.-Nigeria-Revenue-Service-Establishment-Act-2025-1.pdf.pdf",
     ["thecable-gazettes", "kpmg-gaps-2026"]),
    ("JRB Act", None, ["thecable-gazettes", "kpmg-gaps-2026"]),   # no primary text yet
])
def test_reform_act_sources(law_pack, short, primary, secondary):
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        r = s.execute("MATCH (i:Instrument {short: $s}) OPTIONAL MATCH (i)-[:FROM]->(src:Source) "
                      "RETURN src.url AS url, i.secondarySource AS sec, i.verified AS v LIMIT 1", {"s": short})[0]
    assert (r["url"], r["sec"], r["v"]) == (primary, secondary, False)


def test_every_nta_provision_cites_the_gazetted_copy():
    data = loader.read_yaml(RULES)
    nta = [p for p in data["provisions"] if p["instrument"] == "akn/ng/act/2025/7"]
    assert len(nta) == 6 and all(p["source"] == "nta-text" and p.get("secondarySource") for p in nta)
    src = {x["id"]: x for x in data["sources"]}["nta-text"]
    assert src["url"] == NTA_PDF and "Government Notice No. 26" in src["title"]
    assert not any(p.get("verified") for p in nta)


def test_committed_law_pack_is_up_to_date():
    """The committed pack must match the YAML, loader and queries, or `make demo` rebuilds it and dirties
    the tree (fix: `inforce load --allow-unverified --force`, then `inforce export`)."""
    from inforce.paths import LAW_PACK
    meta = loader.pack_meta(LAW_PACK)
    assert meta is not None and meta["hash"] == loader.build_hash(RULES)
    assert meta["embedModel"]  # committed with embeddings, so an offline clone never rebuilds it
