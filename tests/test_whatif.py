import hashlib

import pytest

from inforce import loader
from inforce.demo import copy_demo, replay_agent_fix
from inforce.scan import scan
from inforce.store import open_store
from inforce.whatif import fingerprint, whatif_repeal

from .test_truth import FIXTURE


@pytest.fixture
def pack(tmp_path):
    out = tmp_path / "law.rl"
    loader.load(FIXTURE, out, allow_unverified=True)
    return out


def changes(sec):
    return {(c["kind"], c["id"]): (c["before"], c["after"]) for c in sec["changes"]}


def test_repealing_a_saver_ends_what_it_saved(pack):
    """Truth rule: a savings clause that is itself repealed no longer saves anything."""
    r = whatif_repeal("akn/test/act/new/sec_9", "2026-06-01", pack)
    ch = changes(r["law"])
    assert ch[("Rule", "t.allow.old")] == ("SAVED", "REPEALED")
    assert ch[("Grant", "t.grant.saved")] == ("SAVED", "FELL")
    assert ("Grant", "t.grant.fell") not in ch  # already fell; unchanged


def test_rollback_leaves_store_unchanged(pack):
    r = whatif_repeal("NEWA", "2026-06-01", pack)
    c = r["law"]["counts"]
    assert r["law"]["unchanged"]
    assert c["during"]["nodes"] == c["before"]["nodes"] + 1 and c["during"]["rels"] > c["before"]["rels"]
    assert c["after"] == c["before"]


def test_default_runs_on_a_copy_and_leaves_file_bytes_alone(pack):
    before = hashlib.sha256(pack.read_bytes()).hexdigest()
    whatif_repeal("NEWA", "2026-06-01", pack)
    assert hashlib.sha256(pack.read_bytes()).hexdigest() == before


def test_in_place_restores_content(pack):
    with open_store(pack, read_only=True) as s:
        fp = fingerprint(s)
    r = whatif_repeal("NEWA", "2026-06-01", pack, in_place=True)
    assert r["law"]["unchanged"]
    with open_store(pack, read_only=True) as s:
        assert fingerprint(s) == fp


def test_unknown_target(pack):
    r = whatif_repeal("akn/test/nope", "2026-06-01", pack)
    assert not r["law"]["found"] and r["verdict"] == "NO_CHANGE"


def test_repo_level_fixed_code_turns_stale(tmp_path, law_pack):
    """On the fixed demo, repealing NTA s. 58 would make the new PAYE scale and what uses it STALE."""
    path, _ = law_pack
    repo = copy_demo(tmp_path)
    replay_agent_fix(repo)
    scan(repo, "2026-11-25", path)
    r = whatif_repeal("akn/ng/act/2025/7/sec_58", "2026-11-25", path, repo=repo)
    law_ch = changes(r["law"])
    assert law_ch[("Rule", "ng.pit.band3.2026")] == ("IN_FORCE", "REPEALED")
    repo_ch = changes(r["repo"])
    assert repo_ch[("Artifact", "payroll/paye.py::PIT_BANDS_2026")][1] == "STALE"
    assert repo_ch[("Artifact", "tests/test_paye.py")][1] == "STALE"  # inherited through compute_paye
    assert r["repo"]["unchanged"]
