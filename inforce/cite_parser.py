"""Deterministic claim extraction for `check` (SPEC §5). No model, no network.

Three kinds of claim, all defined in patterns/ng-citations.yaml:
- citation: an Act name, optionally with a section number next to it (known names, then any
  other tax Act by its shape, which the law pack resolves by title or reports as not recognised)
- concept:  a named rule (e.g. "Consolidated Relief Allowance")
- figure:   a percentage in a fixed phrase shape, bound to a rule topic
Repeated mentions of the same thing are merged into one claim (first position kept).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from .paths import PATTERNS_DIR

DEFAULT_PATTERNS = PATTERNS_DIR / "ng-citations.yaml"


@dataclass
class Claim:
    kind: str                    # citation | concept | figure
    text: str                    # the matched words, as written
    line: int                    # 1-based line of the first mention
    start: int                   # char offset of the first mention
    act: str | None = None       # citation: Instrument.short, or the name as written (other_acts)
    section: str | None = None   # citation: section number, if given
    rule: str | None = None      # concept: rule id
    topic: str | None = None     # figure: rule topic
    value: float | None = None   # figure: rate as a fraction (7% -> 0.07)
    amount: str | None = None    # figure: amount as written, digits only (e.g. "300000")
    mentions: int = 1

    @property
    def key(self) -> tuple:
        return (self.kind, self.act, self.section, self.rule, self.topic, self.value, self.amount)


@dataclass
class Patterns:
    acts: list[tuple[str, re.Pattern]] = field(default_factory=list)
    section: re.Pattern | None = None
    other_acts: re.Pattern | None = None
    concepts: list[tuple[str, re.Pattern]] = field(default_factory=list)
    figures: list[tuple[str, re.Pattern]] = field(default_factory=list)


@cache
def load_patterns(path: str | Path = DEFAULT_PATTERNS) -> Patterns:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    p = Patterns()
    for a in doc.get("acts", []):
        # Long names are case-insensitive; all-caps short forms (PITA) must match case.
        alts = [n if n.isupper() else f"(?i:{n})" for n in a["names"]]
        p.acts.append((a["short"], re.compile(r"\b(?:" + "|".join(alts) + r")\b")))
    if doc.get("other_acts"):
        p.other_acts = re.compile(doc["other_acts"])
    if doc.get("section"):
        p.section = re.compile(doc["section"], re.IGNORECASE)
    p.concepts = [(c["rule"], re.compile(c["regex"])) for c in doc.get("concepts", [])]
    p.figures = [(f["topic"], re.compile(f["regex"])) for f in doc.get("figures", [])]
    return p


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _section_near(text: str, start: int, end: int, pat: re.Pattern | None) -> str | None:
    """A section number right before ("section 33 of the X Act") or after ("X Act, s. 33") a name."""
    if pat is None:
        return None
    before = text[max(0, start - 30):start]
    m = None
    for m in re.finditer(pat.pattern + r"\s+of(?:\s+the)?\s*$", before, re.IGNORECASE):
        pass
    if m:
        return m.group("num")
    after = re.match(r"[\s,]*(?:\(\s*)?" + pat.pattern, text[end:end + 25], re.IGNORECASE)
    return after.group("num") if after else None


def extract(text: str, patterns: Patterns | None = None) -> list[Claim]:
    """All claims in `text`, merged by what they refer to, in order of first mention."""
    p = patterns or load_patterns()
    found: list[Claim] = []

    for short, rx in p.acts:
        for m in rx.finditer(text):
            found.append(Claim("citation", m.group(0), _line(text, m.start()), m.start(), act=short,
                               section=_section_near(text, m.start(), m.end(), p.section)))

    # Other tax Acts: only where no known name matched (the law pack resolves them by title).
    known = [(c.start, c.start + len(c.text)) for c in found]
    if p.other_acts is not None:
        for m in p.other_acts.finditer(text):
            if any(s < m.end() and m.start() < e for s, e in known):
                continue
            name = " ".join(m.group(0).split())
            found.append(Claim("citation", name, _line(text, m.start()), m.start(), act=name,
                               section=_section_near(text, m.start(), m.end(), p.section)))

    for rule, rx in p.concepts:
        for m in rx.finditer(text):
            found.append(Claim("concept", m.group(0), _line(text, m.start()), m.start(), rule=rule))

    for topic, rx in p.figures:
        for m in rx.finditer(text):
            gd = m.groupdict()
            amount = re.sub(r"\D", "", gd["amount"]) if gd.get("amount") else None
            found.append(Claim("figure", " ".join(m.group(0).split()), _line(text, m.start()), m.start(),
                               topic=topic, value=round(float(gd["pct"]) / 100, 6), amount=amount))

    merged: dict[tuple, Claim] = {}
    for c in sorted(found, key=lambda c: c.start):
        if c.key in merged:
            merged[c.key].mentions += 1
        else:
            merged[c.key] = c
    # "Personal Income Tax Act (PITA), section 33": a bare mention of an Act that is
    # also cited with a section is the same citation, not a second claim.
    for k, c in list(merged.items()):
        if c.kind == "citation" and c.section is None:
            sectioned = [x for x in merged.values() if x.kind == "citation" and x.act == c.act and x.section]
            if sectioned:
                sectioned[0].mentions += c.mentions
                del merged[k]
    return sorted(merged.values(), key=lambda c: c.start)
