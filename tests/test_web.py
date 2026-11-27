"""The browser checker (web/checker.js) must agree with `inforce check` claim for claim."""
import json
import shutil
import subprocess

import pytest

from inforce.check import check_text
from inforce.export import write_export
from inforce.paths import ROOT

from .test_check import STALE

NODE = shutil.which("node")
TEXTS = [
    STALE.read_text(),
    "Under section 183(2) of the Nigeria Tax Act existing pioneer certificates continue. NTA s. 58 sets the bands.",
    "The first NGN 800,000 at 0% and the next ₦9,000,000 at 18%; rent relief applies. The next ₦500,000 at 17%.",
    "PITA, section 33: the CRA. Companies pay capital gains tax at 10% under CGTA.",
    "Nothing here.",
    "The Stamp Duties Act and the Nigeria Tax Administration Act; section 4 of the Petroleum Profits Tax Act.",
    "The Casino Act; the Taxes and Levies (Approved List for Collection) Act; the Federal Inland Revenue Service "
    "(Establishment) Act.",
]
RUNNER = """
import { check } from %s;
import { readFileSync } from "node:fs";
const data = JSON.parse(readFileSync(process.argv[2], "utf8"));
const cases = JSON.parse(readFileSync(process.argv[3], "utf8"));
console.log(JSON.stringify(cases.map(([t, on]) => check(t, data, on))));
"""


def norm(items):
    return [(i["line"], i["claim"], i["kind"], i["ref"], i["verdict"], i["successorRef"], i["mentions"],
             i["verified"] is True)
            for i in items]


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_checker_matches_python(tmp_path, law_pack):
    path, _ = law_pack
    export = tmp_path / "export.json"
    write_export(path, export)
    cases = [(t, on) for t in TEXTS for on in ("2025-06-01", "2026-03-01")]
    (tmp_path / "cases.json").write_text(json.dumps(cases))
    script = tmp_path / "run.mjs"
    script.write_text(RUNNER % json.dumps((ROOT / "web" / "checker.js").as_uri()))
    out = subprocess.run([NODE, str(script), str(export), str(tmp_path / "cases.json")],
                         capture_output=True, text=True, check=True)
    js = json.loads(out.stdout)
    for (text, on), j in zip(cases, js, strict=True):
        py = check_text(text, on, path)
        assert j["verdict"] == py["verdict"], (text[:40], on)
        assert norm(j["items"]) == norm(py["items"]), (text[:40], on)


def test_committed_export_matches_the_law_pack(tmp_path):
    """web/export.json is regenerated from the committed pack (run `inforce export` after `inforce load`)."""
    from inforce.export import build_export
    from inforce.paths import LAW_PACK
    committed = json.loads((ROOT / "web" / "export.json").read_text())
    fresh = build_export(LAW_PACK)
    for k in ("generated",):
        committed.pop(k), fresh.pop(k)
    assert committed == fresh


def test_export_carries_the_verification_status():
    """The browser page shows the same 'N of M law entries verified' as the README."""
    from inforce import loader
    from inforce.paths import RULES_DIR
    committed = json.loads((ROOT / "web" / "export.json").read_text())
    items = loader.verify_list(RULES_DIR)
    assert committed["verification"] == {"verified": sum(i["verified"] for i in items), "total": len(items),
                                         "summary": loader.verify_summary(RULES_DIR)}
    assert "of " in (ROOT / "web" / "app.js").read_text() and "verification" in (ROOT / "web" / "app.js").read_text()


def test_no_stale_all_unverified_claims():
    """Once entries are verified, the page footer and the YAML header must not say none are."""
    page = (ROOT / "web" / "index.html").read_text()
    assert "come from published commentary on the Nigeria Tax Act" not in page
    assert "Nigeria Tax Act entries are checked against the Act's official editions" in page
    header = (ROOT / "data" / "rules" / "ng-tax-2026.yaml").read_text().split("\n---", 1)[0]
    assert "EVERY entry is verified: false" not in header


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_browser_notes_unknown_start_dates(tmp_path, law_pack):
    from inforce.check import START_UNKNOWN
    path, _ = law_pack
    export = tmp_path / "export.json"
    write_export(path, export)
    cases = [["Under PITA the CRA applies.", "1990-01-01"], ["Under the Nigeria Tax Act.", "2026-03-01"]]
    (tmp_path / "cases.json").write_text(json.dumps(cases))
    script = tmp_path / "run.mjs"
    script.write_text(RUNNER % json.dumps((ROOT / "web" / "checker.js").as_uri()))
    out = subprocess.run([NODE, str(script), str(export), str(tmp_path / "cases.json")],
                         capture_output=True, text=True, check=True)
    old, new = json.loads(out.stdout)
    assert all(START_UNKNOWN in (i["note"] or "") for i in old["items"])
    assert all(START_UNKNOWN not in (i["note"] or "") for i in new["items"])
