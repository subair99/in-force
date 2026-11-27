"""The human verification sheet (docs/VERIFY.md) and applying its ticks to the rule YAML.

`inforce verify --sheet docs/VERIFY.md` writes one checkbox row per law entry, grouped by Act
(NTA first) and section, so the Act's text can be worked through in order.
`inforce verify --apply docs/VERIFY.md` sets `verified: true` on the YAML line of each ticked
row and on nothing else, checks that by re-reading the YAML, and shows the diff. It never sets
anything back to false. InForce itself never decides that an entry is verified.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .loader import LAW_SECTIONS, provision_numbering, read_yaml, verify_list, verify_summary

ROW = re.compile(r"^- \[(?P<tick>[ xX])\] \*\*(?P<kind>[\w]+)\*\* `(?P<entry>[^`]+)`")
ACT_FIRST = "akn/ng/act/2025/7"  # the NTA: the Act being checked


def _section_key(s: str) -> tuple:
    if s == "the Act itself":
        return (0, 0, "")
    if s == "repeals made by this Act":
        return (3, 0, "")
    m = re.match(r"(?:section\s+)?(\d+)", s or "")
    return (1, int(m.group(1)), s) if m else (2, 0, s or "")


def _homes(data: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], tuple[str, str]]:
    """(kind, entry) -> (Act akn, section label): where in which Act each entry is checked."""
    prov = {p["akn"]: p for p in data.get("provisions", [])}
    rule = {r["id"]: r for r in data.get("rules", [])}
    acts = {i["akn"] for i in data.get("instruments", [])}

    def of_prov(akn: str) -> tuple[str, str]:
        p = prov.get(akn)
        if not p:
            return ("(unknown Act)", "section not recorded")
        number, _, note = provision_numbering(p)
        # "section 182(2)", but a location that is not a number stands alone ("long title (Commencement)")
        where = f"section {number}" if str(number)[:1].isdigit() else str(number)
        return (p["instrument"], where + (f" ({note})" if note else ""))

    def of_rule(rid: str) -> tuple[str, str]:
        r = rule.get(rid)
        return of_prov(r["provision"]) if r else ("(unknown Act)", "section not recorded")

    out = {}
    for e in data.get("instruments", []):
        out[("instrument", e["akn"])] = (e["akn"], "the Act itself")
    for e in data.get("provisions", []):
        out[("provision", e["akn"])] = of_prov(e["akn"])
    for e in data.get("rules", []):
        out[("rule", e["id"])] = of_rule(e["id"])
    for e in data.get("repeals", []):
        out[("repeal", f"{e['by']} -> {e['target']}")] = (e["by"], "repeals made by this Act")
    for e in data.get("replacements", []):
        out[("replacement", f"{e['old']} -> {e['new']}")] = of_rule(e["new"])
    for e in data.get("successions", []):
        out[("succession", f"{e['old']} -> {e['new']}")] = of_prov(e["new"])
    for e in data.get("related", []):
        out[("related", f"{e['rule']} -> {e['related']}")] = of_rule(e["related"])
    for e in data.get("grants", []):
        gu = e.get("grantedUnder")
        out[("grant", e["id"])] = (gu, "the Act itself") if gu in acts else of_prov(gu)
    for e in data.get("savings", []):
        out[("saving", f"{e['saver']} -> {e['saves']}")] = of_prov(e["saver"])
    return out


def _what(kind: str, e: dict[str, Any], data: dict[str, Any]) -> str:
    titles = {i["akn"]: i.get("title") or i["akn"] for i in data.get("instruments", [])}
    texts = {r["id"]: r.get("text") for r in data.get("rules", [])}
    if kind == "instrument":
        note = (f"; commencement in: {e['commencementSection']}" if e.get("commencementSection") else "") + \
               (f"; note: {e['note']}" if e.get("note") else "")
        return (f"title \"{e.get('title')}\"; assented {e.get('assentedOn', '-')}; "
                f"commences {e.get('commencesOn', '-')}{note}")
    if kind == "provision":
        dates = ", ".join(x for x in (f"in force from {e['validFrom']}" if e.get("validFrom") else "",
                                      f"until {e['validTo']}" if e.get("validTo") else "") if x)
        nums = e.get("numbers") or {}
        if nums:
            where = "; ".join(
                f"{ed} text: \"{d['number']}\"" + (f" (p. {d['page']})" if d.get("page") else "")
                + (f" says \"{d['text']}\"" if d.get("text") else "")
                + (f" [{d['note']}]" if d.get("note") else "") for ed, d in nums.items())
            if "certified" not in nums:
                where += "; certified numbering not yet checked"
        else:
            where = f"section number \"{e.get('number')}\""
        extra = f"; note: {e['note']}" if e.get("note") else ""
        return f"{where}; {dates or 'no dates'}; summary \"{e.get('summary')}\"{extra}"
    if kind == "rule":
        val = f"value {e['value']} {e.get('unit') or ''}".strip() if e.get("value") is not None else "no value"
        also = f"; also set by {', '.join(e['alsoProvisions'])}" if e.get("alsoProvisions") else ""
        provs = {p_["akn"]: p_ for p_ in data.get("provisions", [])}
        for akn in [e.get("provision"), *(e.get("alsoProvisions") or [])]:
            if provs.get(akn, {}).get("note"):
                also += f"; note ({akn.rsplit('/', 1)[-1]}): {provs[akn]['note']}"
        return f"{val}; says \"{e.get('text')}\"{also}"
    if kind == "repeal":
        bp = next((p for p in data.get("provisions", []) if p["akn"] == e.get("byProvision")), None)
        if bp:
            number, _, note = provision_numbering(bp)
            sec = f" under section {number}" + (f" ({note})" if note else "")
        else:
            sec = f" under section {e['section']}" if e.get("section") else ""
        eds = e.get("editions") or {}
        listed = ("; listed at " + ", ".join(f"{k} {v}" for k, v in eds.items())) if eds else ""
        note = f"; note: {e['note']}" if e.get("note") else ""
        return f"repeals {titles.get(e['target'], e['target'])} on {e.get('on')}{sec}{listed}{note}"
    if kind == "replacement":
        return f"\"{texts.get(e['old'])}\" is replaced one-to-one by \"{texts.get(e['new'])}\""
    if kind == "succession":
        return f"replaced as a whole: {e.get('note') or ''}"
    if kind == "related":
        return f"related, not a successor: {e.get('note') or ''}"
    if kind == "grant":
        return f"\"{e.get('title')}\" rests on this Act or section"
    if kind == "saving":
        until = e.get("until") or "no end date"
        return f"saves {e['saves']} until {until}; {e.get('note') or ''}".rstrip("; ")
    return ""


def _entry_of(kind: str, e: dict[str, Any]) -> str:
    pairs = {"repeal": ("by", "target"), "replacement": ("old", "new"), "succession": ("old", "new"),
             "related": ("rule", "related"), "saving": ("saver", "saves")}
    if kind in pairs:
        a, b = pairs[kind]
        return f"{e[a]} -> {e[b]}"
    return e.get("akn") or e["id"]


def read_ticks(sheet: str | Path) -> dict[tuple[str, str], bool]:
    out = {}
    if Path(sheet).exists():
        for line in Path(sheet).read_text(encoding="utf-8").splitlines():
            m = ROW.match(line)
            if m:
                out[(m["kind"], m["entry"])] = m["tick"] in "xX"
    return out


def build_sheet(rules_dir: str | Path, keep_ticks: dict[tuple[str, str], bool] | None = None) -> str:
    data = read_yaml(Path(rules_dir))
    homes = _homes(data)
    listed = {(i["kind"], i["entry"]): i for i in verify_list(rules_dir)}
    titles = {i["akn"]: (i.get("short"), i.get("title")) for i in data.get("instruments", [])}
    keep_ticks = keep_ticks or {}

    groups: dict[str, dict[str, list[str]]] = {}
    for sec in LAW_SECTIONS:
        kind = sec[:-1] if sec != "related" else "related"
        for e in data.get(sec, []):
            entry = _entry_of(kind, e)
            act, section = homes.get((kind, entry), ("(unknown Act)", "section not recorded"))
            info = listed[(kind, entry)]
            ticked = info["verified"] or keep_ticks.get((kind, entry), False)
            if not info["source"]:
                src = "**no source**"
            elif str(info["source"]).startswith("http"):
                src = f"[{info.get('sourceLabel') or 'source'}]({info['source']})"
            else:  # a citation rather than a URL
                src = f"source: {info['source']}"
            if info.get("page"):
                src += f", p. {info['page']}"
            if info.get("secondarySources"):
                src += " (secondary: " + ", ".join(f"[{n}]({u})" for n, u in
                                                   enumerate(info["secondarySources"], 1)) + ")"
            row = (f"- [{'x' if ticked else ' '}] **{kind}** `{entry}`: check {_what(kind, e, data)}. "
                   f"{src} · `{info['where']}`" + (" · already verified" if info["verified"] else ""))
            groups.setdefault(act, {}).setdefault(section, []).append(row)

    order = sorted(groups, key=lambda a: (a != ACT_FIRST, (titles.get(a) or ("", a))[0] or a))
    lines = [
        "# InForce verification sheet",
        "",
        "Private working file (docs/ is never committed). Generated by `inforce verify --sheet docs/VERIFY.md`.",
        "",
        f"Status: {verify_summary(rules_dir)}",
        "",
        "How to use: check each row against the Act's text. Tick `[x]` only what the Act confirms, then run",
        "`inforce verify --apply docs/VERIFY.md` (add `--dry-run` to preview). That sets `verified: true` on the",
        "ticked rows in the rule YAML, shows the diff, and changes nothing else. If a value is wrong, do not tick",
        "it: fix it in the YAML yourself first. Regenerating this sheet keeps your ticks.",
        "",
    ]
    for act in order:
        short, title = titles.get(act, (None, act))
        lines += [f"## {short or act}: {title or act}" + ("" if act in titles else ""), ""]
        for section in sorted(groups[act], key=_section_key):
            lines += [f"### {section[0].upper() + section[1:]}", ""] + groups[act][section] + [""]
    return "\n".join(lines).rstrip() + "\n"


def write_sheet(rules_dir: str | Path, sheet: str | Path) -> int:
    """Write the sheet, keeping ticks already in it. Returns the number of rows."""
    text = build_sheet(rules_dir, read_ticks(sheet))
    Path(sheet).parent.mkdir(parents=True, exist_ok=True)
    Path(sheet).write_text(text, encoding="utf-8")
    return sum(1 for line in text.splitlines() if ROW.match(line))


@dataclass
class ApplyResult:
    applied: list[str] = field(default_factory=list)
    already: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    diff: str = ""


def _set_verified(lines: list[str], idx: int) -> None:
    """Set verified: true on the YAML entry starting at line idx (flow `{...}` or block style)."""
    line = lines[idx]
    if "{" in line and line.rstrip().endswith("}"):
        if re.search(r"\bverified:\s*\w+", line):
            lines[idx] = re.sub(r"\bverified:\s*\w+", "verified: true", line)
        else:
            lines[idx] = line.rstrip()[:-1].rstrip() + ", verified: true}"
        return
    dash = len(line) - len(line.lstrip())  # block style: "- key: value" then indented keys
    key_indent = dash + 2
    j = idx + 1
    while j < len(lines):
        s = lines[j]
        ind = len(s) - len(s.lstrip())
        if s.strip() and ind <= dash:
            break
        if ind == key_indent and re.match(r"\s*verified:\s*\w+", s):
            lines[j] = " " * key_indent + "verified: true"
            return
        j += 1
    lines.insert(idx + 1, " " * key_indent + "verified: true")


def apply_ticks(sheet: str | Path, rules_dir: str | Path, dry_run: bool = False) -> ApplyResult:
    res = ApplyResult()
    ticks = {k for k, v in read_ticks(sheet).items() if v}
    before = {(i["kind"], i["entry"]): i for i in verify_list(rules_dir)}
    edits: dict[str, list[int]] = {}
    for key in sorted(ticks):
        item = before.get(key)
        label = f"{key[0]} {key[1]}"
        if item is None:
            res.unknown.append(label)
        elif item["verified"]:
            res.already.append(label)
        else:
            fname, line = item["where"].rsplit(":", 1)
            edits.setdefault(fname, []).append(int(line) - 1)
            res.applied.append(label)

    originals, updated = {}, {}
    for fname, idxs in edits.items():
        path = Path(rules_dir) / fname
        originals[path] = path.read_text(encoding="utf-8")
        lines = originals[path].splitlines()
        for idx in sorted(idxs, reverse=True):  # bottom-up, so inserted lines don't shift later targets
            _set_verified(lines, idx)
        updated[path] = "\n".join(lines) + ("\n" if originals[path].endswith("\n") else "")
        res.diff += "".join(difflib.unified_diff(originals[path].splitlines(True), updated[path].splitlines(True),
                                                 fromfile=f"a/{fname}", tofile=f"b/{fname}"))
    if dry_run or not updated:
        return res
    for path, text in updated.items():
        path.write_text(text, encoding="utf-8")
    # Check: exactly the ticked entries flipped to verified, nothing else changed.
    try:
        after = {(i["kind"], i["entry"]): i for i in verify_list(rules_dir)}
        flipped = {k for k in before if after[k]["verified"] and not before[k]["verified"]}
        wanted = {tuple(x.split(" ", 1)) for x in res.applied}
        changed_other = {k for k in before if {**before[k], "verified": None, "where": None}
                         != {**after[k], "verified": None, "where": None}}
        if flipped != wanted or changed_other:
            raise RuntimeError(f"unexpected change: flipped={sorted(flipped)} other={sorted(changed_other)}")
    except Exception:
        for path, text in originals.items():  # restore the YAML exactly as it was
            path.write_text(text, encoding="utf-8")
        raise
    return res
