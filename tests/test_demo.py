from typer.testing import CliRunner

from inforce.cli import app
from inforce.demo import AGENT_LOG, copy_demo, replay_agent_fix
from inforce.scan import scan


def test_replay_reaches_zero_stale(tmp_path, law_pack):
    path, _ = law_pack
    repo = copy_demo(tmp_path)
    rp = replay_agent_fix(repo, AGENT_LOG)
    assert rp.edits >= 8 and not rp.skipped
    r = scan(repo, "2026-11-25", path)
    assert [a["id"] for a in r["artifacts"] if a["status"] == "STALE"] == []


def test_demo_fast_passes_every_step(law_pack):
    path, _ = law_pack
    res = CliRunner().invoke(app, ["demo", "--fast", "--law", str(path)])
    assert res.exit_code == 0, res.output[-2000:]
    assert res.output.count("PASS") >= 6 and "FAIL" not in res.output
