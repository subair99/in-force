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
    # The README pastes this summary: it must match a real run.
    from inforce.paths import ROOT
    ran = [ln.rstrip() for ln in res.output.splitlines() if ln.startswith("  PASS")]
    pasted = [ln.rstrip() for ln in (ROOT / "README.md").read_text().splitlines() if ln.startswith("  PASS")]
    # (the test runner renders 80 columns wide, so a long line may be cut where Rich wraps it)
    assert len(pasted) == len(ran) and all(p.startswith(r) for p, r in zip(pasted, ran, strict=True))


def test_demo_states_the_true_verification_status(law_pack):
    """Step 1 must give the same 'N of M law entries verified' as the loader, not 'all unverified'."""
    from inforce import loader
    from inforce.paths import RULES_DIR
    path, _ = law_pack
    res = CliRunner(env={"COLUMNS": "400"}).invoke(app, ["demo", "--fast", "--law", str(path)])
    assert res.exit_code == 0, res.output[-2000:]
    assert loader.verify_summary(RULES_DIR) in res.output
    assert "All rules are unverified" not in res.output
