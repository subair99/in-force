import json

from typer.testing import CliRunner

from inforce.cli import app

from .test_check import STALE

runner = CliRunner()


def test_check_exit_3_on_stale(law_pack):
    path, _ = law_pack
    res = runner.invoke(app, ["check", str(STALE), "--on", "2026-03-01", "--law", str(path)])
    assert res.exit_code == 3, res.output
    assert "REPEALED" in res.output
    assert "not legal or tax advice" in res.output


def test_check_json_envelope(law_pack):
    path, _ = law_pack
    res = runner.invoke(app, ["check", "the first ₦300,000 at 7%", "--on", "2026-03-01", "--json",
                              "--law", str(path)])
    assert res.exit_code == 3
    env = json.loads(res.stdout)
    assert set(env) >= {"verdict", "items", "path", "on", "disclaimer"}
    assert env["items"][0]["successorRef"] == "ng.pit.band1.2026"


def test_check_exit_0_when_not_stale(law_pack):
    path, _ = law_pack
    res = runner.invoke(app, ["check", "Under the Nigeria Tax Act.", "--on", "2026-03-01", "--law", str(path)])
    assert res.exit_code == 0, res.output


def test_check_bad_date(law_pack):
    path, _ = law_pack
    res = runner.invoke(app, ["check", "x", "--on", "01/03/2026", "--law", str(path)])
    assert res.exit_code == 1


def test_fallout_iditra(law_pack):
    path, _ = law_pack
    res = runner.invoke(app, ["fallout", "IDITRA", "--on", "2026-03-01", "--json", "--law", str(path)])
    assert res.exit_code == 0, res.output
    env = json.loads(res.stdout)
    assert env["status"] == "REPEALED"
    [row] = env["items"]
    assert row["verdict"] == "SAVED" and row["savedBy"] == "akn/ng/act/2025/7/sec_182_2"
