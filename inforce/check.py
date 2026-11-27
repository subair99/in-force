"""`inforce check`: is each claim in a text still backed by law in force on a date?

Claims come from cite_parser (no model). Every verdict comes from a Cypher
query against the law pack (law.py). Nothing here decides law in Python.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import law
from .cite_parser import Claim, extract
from .store import Store, open_store

DISCLAIMER = "InForce checks whether a provision is in force. It is not legal or tax advice."
STALE_STATUSES = ("REPEALED",)


@dataclass
class Item:
    line: int
    claim: str
    kind: str
    ref: str | None
    verdict: str                     # IN_FORCE | REPEALED | SAVED | NOT_YET | NOT_RECOGNISED | UNKNOWN
    verified: bool = False
    endedOn: str | None = None
    repealedBy: str | None = None
    successor: str | None = None     # what replaced it, in words
    successorRef: str | None = None
    successorStatus: str | None = None
    source: str | None = None
    sourceTitle: str | None = None   # what the source is, when its URL alone could mislead
    path: list[str] = field(default_factory=list)
    note: str | None = None
    mentions: int = 1
    successorScale: list[dict[str, Any]] | None = None   # the whole new scale, when replaced as a whole
    related: list[dict[str, Any]] = field(default_factory=list)  # read together; not successors
    ruleNotes: list[str] = field(default_factory=list)       # notes on the provisions setting the cited rule
    successorNotes: list[str] = field(default_factory=list)  # ... and on its successor's provisions


def _d(v: Any) -> str | None:
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def _rule_item(c: Claim, r: dict[str, Any]) -> Item:
    succ = r["successors"][0] if r["successors"] else None
    scale = r.get("scale")
    if succ:
        successor, ref, status = succ["text"], succ["id"], succ["status"]
    elif scale:  # replaced as a whole: the successor is the new scale, not one band
        successor, ref, status = law.scale_text(scale), scale["provision"], scale["status"]
    else:
        successor = ref = status = None
    notes = [] if r["verified"] else ["rule not yet verified against the Act's text"]
    notes += r.get("notes", [])
    succ_notes = succ.get("notes", []) if succ else []
    notes += [f"successor {n}" for n in succ_notes]
    if r["status"] == "REPEALED" and not successor:
        notes.append("ended with no replacement")
    notes += [f"related (not a successor): {x['text']} ({x['id']})" for x in r.get("related", [])]
    return Item(
        line=c.line, claim=c.text, kind=c.kind, ref=r["id"], verdict=r["status"], verified=r["verified"],
        endedOn=_d(r["endedOn"]), repealedBy=r["repealedBy"],
        successor=successor, successorRef=ref, successorStatus=status,
        successorScale=scale["rules"] if scale else None,
        ruleNotes=r.get("notes", []), successorNotes=succ_notes,
        related=[{"id": x["id"], "text": x["text"]} for x in r.get("related", [])],
        source=r["source"], sourceTitle=r.get("sourceTitle"), path=r["path"], mentions=c.mentions, note="; ".join(notes) or None,
    )


def _numbers(text: str | None) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", text or "")}


def resolve(store: Store, c: Claim, on: str) -> list[Item]:
    if c.kind == "concept":
        r = law.rule_status(store, c.rule, on)
        if r is None:
            return [Item(c.line, c.text, c.kind, c.rule, "NOT_RECOGNISED", note=f"rule {c.rule} not in law pack")]
        return [_rule_item(c, r)]

    if c.kind == "figure":
        rules = [law.rule_status(store, rid, on) for rid in law.rules_by_value(store, c.topic, c.value)]
        if c.amount:  # "first NGN 300,000 at 7%": the amount must also be the rule's
            rules = [r for r in rules if c.amount in _numbers(r["text"])]
        if not rules:
            return [Item(c.line, c.text, c.kind, None, "NOT_RECOGNISED", mentions=c.mentions,
                         note=f"no {c.topic} rule in the law pack has this figure")]
        return [_rule_item(c, r) for r in rules]

    # citation
    note = None
    if c.section:
        found = law.provision_lookup(store, c.act, c.section)
        akn = found["akn"] if found else None
        if akn:
            st = law.provision_status(store, akn, on)
            inst = law.instrument_status(store, c.act, on)
            path = [f"Provision {akn}", f"<-CONTAINS- Instrument {c.act}"]
            if st["endedOn"] and st["repealedBy"]:
                path.append(f"<-REPEALS {st['endedOn']}- Instrument {st['repealedByShort'] or st['repealedBy']}")
            return [Item(c.line, c.text + f" s. {c.section}", c.kind, akn, st["status"],
                         verified=st["verified"] is True, endedOn=_d(st["endedOn"]), repealedBy=st["repealedBy"],
                         source=inst["source"] if inst else None,
                         sourceTitle=inst["sourceTitle"] if inst else None, path=path, mentions=c.mentions,
                         note="; ".join(filter(None, [
                             None if found["current"] == c.section else
                             f"s.{c.section} is s.{found['current']} in the certified (current) text",
                             found["note"] if found["current"] != c.section else None,
                             None if st["verified"] is True else "provision not yet verified"])) or None)]
        note = f"section {c.section} is not in the law pack; status is for the whole Act"
    inst = law.instrument_status(store, c.act, on)
    if inst is None:
        return [Item(c.line, c.text, c.kind, c.act, "NOT_RECOGNISED", mentions=c.mentions,
                     note=f"Act {c.act} not in law pack")]
    verified = inst["instrumentVerified"] is True and (inst["verified"] is True or inst["status"] != "REPEALED")
    if not verified:
        note = "; ".join(filter(None, [note, "Act or repeal not yet verified"]))
    return [Item(c.line, c.text + (f" s. {c.section}" if c.section else ""), c.kind, inst["akn"], inst["status"],
                 verified=verified, endedOn=_d(inst["endedOn"]), repealedBy=inst["repealedBy"],
                 successor=inst["repealedByTitle"], successorRef=inst["repealedBy"],
                 successorStatus="IN_FORCE" if inst["repealedBy"] else None,
                 source=inst["source"], sourceTitle=inst["sourceTitle"], path=inst["path"], note=note, mentions=c.mentions)]


def overall(items: list[Item]) -> str:
    """STALE if anything rests on repealed law; SUSPECT if anything is unverified,
    unrecognised or not yet in force; CURRENT otherwise; NO_CLAIMS if nothing was found."""
    if not items:
        return "NO_CLAIMS"
    if any(i.verdict in STALE_STATUSES for i in items):
        return "STALE"
    if any(not i.verified or i.verdict in ("NOT_RECOGNISED", "NOT_YET", "UNKNOWN") for i in items):
        return "SUSPECT"
    return "CURRENT"


def check_text(text: str, on: str, law_pack: str | Path, log=None) -> dict[str, Any]:
    """Check a text. Returns the JSON envelope: {verdict, items, path, on, disclaimer}."""
    claims = extract(text)
    items: list[Item] = []
    with open_store(law_pack, read_only=True, log=log) as store:
        for c in claims:
            items.extend(resolve(store, c, on))
    return {
        "verdict": overall(items),
        "on": on,
        "items": [asdict(i) for i in items],
        "path": [" ".join(i.path) for i in items if i.verdict in STALE_STATUSES],
        "unverified": any(not i.verified for i in items),
        "disclaimer": DISCLAIMER,
    }
