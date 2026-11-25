"""Truth rules: in force on a date, repeal, saving clause, successor chain, fallout.

Runs against tests/fixtures/law/test-law.yaml (fictional law) loaded through the real loader.
"""
import pytest

from inforce import law, loader
from inforce.store import open_store

from .conftest import ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "law"


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("truth") / "law.rl"
    loader.load(FIXTURE, out, allow_unverified=True)
    return out


def status(pack, akn, on):
    with open_store(pack, read_only=True) as s:
        return law.provision_status(s, akn, on)


@pytest.mark.parametrize("akn,on,expected", [
    # repealed through its Act only
    ("akn/test/act/old/sec_1", "2025-12-31", "IN_FORCE"),
    ("akn/test/act/old/sec_1", "2026-01-01", "REPEALED"),
    # its own validTo comes first
    ("akn/test/act/old/sec_2", "2025-06-30", "IN_FORCE"),
    ("akn/test/act/old/sec_2", "2025-07-01", "REPEALED"),
    # saving clause: saved from repeal until 2027-01-01, then repealed
    ("akn/test/act/old/sec_3", "2025-12-31", "IN_FORCE"),
    ("akn/test/act/old/sec_3", "2026-06-01", "SAVED"),
    ("akn/test/act/old/sec_3", "2027-01-01", "REPEALED"),
    # commencement from the Act when the provision has no validFrom
    ("akn/test/act/new/sec_1", "2025-12-31", "NOT_YET"),
    ("akn/test/act/new/sec_1", "2026-01-01", "IN_FORCE"),
    # its own validFrom wins over the Act's
    ("akn/test/act/new/sec_2", "2026-03-01", "NOT_YET"),
    ("akn/test/act/new/sec_2", "2026-07-01", "IN_FORCE"),
])
def test_provision_status(pack, akn, on, expected):
    assert status(pack, akn, on)["status"] == expected


def test_repeal_details(pack):
    st = status(pack, "akn/test/act/old/sec_1", "2026-03-01")
    assert st["endedOn"].isoformat() == "2026-01-01"
    assert st["repealedBy"] == "akn/test/act/new"


def test_saved_names_saver(pack):
    st = status(pack, "akn/test/act/old/sec_3", "2026-06-01")
    assert st["savers"] == ["akn/test/act/new/sec_9"]


def test_unknown_provision_is_none(pack):
    assert status(pack, "akn/test/nope", "2026-01-01") is None


def test_rule_takes_provision_status_and_follows_successor_chain(pack):
    with open_store(pack, read_only=True) as s:
        r = law.rule_status(s, "t.band.old", "2026-08-01")
    assert r["status"] == "REPEALED"
    # chain old -> mid -> new; the successor shown is the one in force on the date
    assert [x["id"] for x in r["successors"]] == ["t.band.new"]
    assert r["successors"][0]["status"] == "IN_FORCE"
    assert r["path"]  # proof path present


def test_successor_on_earlier_date_is_middle_rule(pack):
    with open_store(pack, read_only=True) as s:
        r = law.rule_status(s, "t.band.old", "2026-03-01")
    assert [x["id"] for x in r["successors"]] == ["t.band.mid"]


def test_rule_verified_flag(pack):
    with open_store(pack, read_only=True) as s:
        assert law.rule_status(s, "t.unver", "2026-03-01")["verified"] is False
        assert law.rule_status(s, "t.band.mid", "2026-03-01")["verified"] is True


def test_rules_by_value(pack):
    with open_store(pack, read_only=True) as s:
        assert law.rules_by_value(s, "band", 0.07) == ["t.band.old"]
        assert law.rules_by_value(s, "band", 0.99) == []


@pytest.mark.parametrize("ref,on,expected", [
    ("OLDA", "2025-12-31", "IN_FORCE"),
    ("OLDA", "2026-01-01", "REPEALED"),
    ("akn/test/act/old", "2026-01-01", "REPEALED"),
    ("NEWA", "2025-12-31", "NOT_YET"),
    ("NEWA", "2026-01-01", "IN_FORCE"),
])
def test_instrument_status(pack, ref, on, expected):
    with open_store(pack, read_only=True) as s:
        assert law.instrument_status(s, ref, on)["status"] == expected


def test_provision_by_number(pack):
    with open_store(pack, read_only=True) as s:
        assert law.provision_by_number(s, "OLDA", "3") == "akn/test/act/old/sec_3"
        assert law.provision_by_number(s, "OLDA", "77") is None


def test_fallout(pack):
    with open_store(pack, read_only=True) as s:
        rows = {r["dependent"]: r for r in law.fallout(s, "INCA", "2026-03-01")}
    assert rows["Saved certificate"]["verdict"] == "SAVED"
    assert rows["Saved certificate"]["savedBy"] == "akn/test/act/new/sec_9"
    assert rows["Lapsed certificate"]["verdict"] == "FELL"
    assert rows["Act-level grant"]["verdict"] == "FELL"


def test_fallout_before_repeal_stands(pack):
    with open_store(pack, read_only=True) as s:
        rows = law.fallout(s, "INCA", "2025-06-01")
    assert {r["verdict"] for r in rows} == {"STANDS"}


def test_known_on_versions(tmp_path):
    """Bitemporal: which version of an Act was on record on a date; unknown start dates are flagged."""
    import yaml
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "x.yaml").write_text(yaml.safe_dump({
        "instruments": [{"akn": "i/1", "short": "ACT", "verified": True, "versions": [
            {"version": "gazetted", "recordedAt": "TODO", "closedAt": __import__("datetime").date(2026, 1, 6)},
            {"version": "certified", "recordedAt": __import__("datetime").date(2026, 1, 6)}]}],
        "provisions": [{"akn": "p/1", "instrument": "i/1", "verified": True,
                        "recordedAt": __import__("datetime").date(2026, 1, 6)}],
    }))
    out = tmp_path / "x.rl"
    report = loader.load(tmp_path / "rules", out, embed=False)
    assert any("not a date" in w for w in report.warnings)
    with open_store(out, read_only=True) as s:
        d = law.diff_known_on(s, "2026-01-02", "2026-02-01")
    [act] = d["acts"]
    assert [v["version"] for v in act["d1"]] == ["gazetted"] and act["d1"][0]["startUnknown"]
    assert [v["version"] for v in act["d2"]] == ["certified"] and act["changed"]
    assert d["provisions"] == [{"akn": "p/1", "summary": None, "d1": False, "d2": True}]
    with open_store(out, read_only=True) as s:
        same = law.diff_known_on(s, "2026-02-01", "2026-03-01")
    assert not same["acts"][0]["changed"] and same["provisions"] == []


@pytest.mark.parametrize("on,expected", [("2025-12-31", "NOT_YET"), ("2026-01-02", "IN_FORCE")])
def test_rent_relief_starts_with_the_nta(law_pack, on, expected):
    """Rent relief is an NTA rule: not in force before 1 Jan 2026 (it used to read IN_FORCE in 2025)."""
    path, _ = law_pack
    with open_store(path, read_only=True) as s:
        assert law.rule_status(s, "ng.pit.rent_relief.2026", on)["status"] == expected


def test_loader_warns_on_new_act_provision_without_valid_from(tmp_path):
    import datetime as dt

    import yaml
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "x.yaml").write_text(yaml.safe_dump({
        "instruments": [{"akn": "i/new", "commencesOn": dt.date(2026, 1, 1), "verified": True}],
        "provisions": [{"akn": "i/new/s1", "instrument": "i/new", "verified": True},
                       {"akn": "i/new/s2", "instrument": "i/new", "validFrom": dt.date(2026, 1, 1), "verified": True}],
    }))
    report = loader.load(tmp_path / "rules", tmp_path / "x.rl", embed=False)
    warned = [w for w in report.warnings if "no validFrom" in w]
    assert len(warned) == 1 and "i/new/s1" in warned[0]
