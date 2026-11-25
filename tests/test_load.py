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
