import shutil

import pytest

from inforce import loader
from inforce.verify_sheet import apply_ticks, read_ticks, write_sheet

from .conftest import RULES


@pytest.fixture
def rules(tmp_path):
    d = tmp_path / "rules"
    shutil.copytree(RULES, d)
    return d


def tick(sheet, *keys):
    lines = sheet.read_text().splitlines()
    for i, line in enumerate(lines):
        if any(f"**{k}** `{e}`" in line for k, e in keys):
            lines[i] = line.replace("- [ ]", "- [x]", 1)
    sheet.write_text("\n".join(lines) + "\n")


def verified(rules_dir):
    return {(i["kind"], i["entry"]) for i in loader.verify_list(rules_dir) if i["verified"]}


def test_sheet_has_one_row_per_entry_nta_first_sections_in_order(rules, tmp_path):
    sheet = tmp_path / "VERIFY.md"
    n = write_sheet(rules, sheet)
    assert n == len(loader.verify_list(rules))
    text = sheet.read_text()
    assert text.index("## NTA") < text.index("## PITA")
    nta = text[text.index("## NTA"):text.index("## CGTA")]
    assert nta.index("Section 27(1)") < nta.index("Section 56") < nta.index("Section 58") < nta.index("Section 155(4)")
    assert "0 of" in text


def test_apply_sets_only_ticked_rows(rules, tmp_path):
    sheet = tmp_path / "VERIFY.md"
    write_sheet(rules, sheet)
    picks = [("rule", "ng.pit.band3.2026"),                                    # flow style with verified: false
             ("instrument", "akn/ng/act/2025/7"),                             # block style, no verified key
             ("repeal", "akn/ng/act/2025/7 -> TODO/ng/act/pita"),             # relationship row
             ("replacement", "ng.cgt.company.old -> ng.cgt.company.2026")]   # flow style, no verified key
    tick(sheet, *picks)
    dry = apply_ticks(sheet, rules, dry_run=True)
    assert len(dry.applied) == 4 and "+  - {id: ng.pit.band3.2026" in dry.diff
    assert verified(rules) == set()  # dry run wrote nothing
    res = apply_ticks(sheet, rules)
    assert verified(rules) == set(picks)
    added = [ln for ln in res.diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln for ln in res.diff.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    assert len(added) == 4 and len(removed) == 3  # 3 lines edited + 1 inserted (block-style Act), nothing else
    # applying again changes nothing; regenerating keeps ticks
    again = apply_ticks(sheet, rules)
    assert again.applied == [] and len(again.already) == 4
    write_sheet(rules, sheet)
    assert {k for k, v in read_ticks(sheet).items() if v} == set(picks)
    # the YAML still loads (as verified entries where ticked)
    report = loader.load(rules, tmp_path / "x.rl", allow_unverified=True, embed=False)
    assert report.counts["Rule"] > 0


def test_unticked_rows_are_never_set_and_unknown_rows_are_reported(rules, tmp_path):
    sheet = tmp_path / "VERIFY.md"
    write_sheet(rules, sheet)
    sheet.write_text(sheet.read_text() + "- [x] **rule** `ng.not.a.rule`: made up\n")
    res = apply_ticks(sheet, rules)
    assert res.applied == [] and res.unknown == ["rule ng.not.a.rule"]
    assert verified(rules) == set()
