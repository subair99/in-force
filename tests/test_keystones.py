from typer.testing import CliRunner

from inforce import law
from inforce.cli import app
from inforce.scan import scan
from inforce.store import open_store

from .test_scan import repo  # noqa: F401  (fixture)


def test_keystones_rank_by_direct_plus_downstream(repo, law_pack):  # noqa: F811
    path, _ = law_pack
    scan(repo, "2026-03-01", path)
    with open_store(repo / ".inforce" / "project.rl", read_only=True) as s:
        rows = law.keystones(s, "2026-03-01")
    top = rows[0]
    assert top["rule"] == "ng.pit.cra.old" and top["status"] == "REPEALED"
    # encoded by two constants, cited by the policy page and the answer
    assert set(top["directArtifacts"]) == {"payroll/paye.py::CRA_RATE", "payroll/paye.py::CRA_FLAT_MIN",
                                           "docs/hr-policy.md", "answers/stale_answer.md"}
    assert "tests/test_paye.py" in top["downstreamArtifacts"]
    assert not set(top["directArtifacts"]) & set(top["downstreamArtifacts"])
    assert [r["weight"] for r in rows] == sorted((r["weight"] for r in rows), reverse=True)


def test_keystones_cli_needs_a_scan(tmp_path):
    res = CliRunner().invoke(app, ["keystones", str(tmp_path)])
    assert res.exit_code == 1
