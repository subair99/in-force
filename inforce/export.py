"""`inforce export`: web/export.json for the static browser checker.

The page decides nothing itself. Statuses are computed here by the usual Cypher queries,
once for each date at which any status can change (status is constant between them), and the
page looks up the last change date on or before the date the visitor picks. Claim patterns
are the same ones `check` uses, converted to JavaScript regex syntax.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml

from . import law
from .check import DISCLAIMER, START_UNKNOWN, start_unknown
from .cite_parser import DEFAULT_PATTERNS
from .store import open_store

BEFORE_ALL = "0001-01-01"

def py_to_js(pattern: str, flags: str = "u") -> dict[str, str]:
    """A Python regex as {source, flags} for JavaScript's RegExp: leading (?i) -> flag i, (?P<n> -> (?<n>."""
    if pattern.startswith("(?i)"):
        pattern, flags = pattern[4:], flags + "i"
    return {"source": pattern.replace("(?P<", "(?<"), "flags": "".join(sorted(set(flags)))}

def js_patterns(path: Path = DEFAULT_PATTERNS) -> dict[str, Any]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {
        # one regex per alias: all-caps short forms are case-sensitive, long names are not
        "acts": [{"short": a["short"], "aliases": [py_to_js(r"\b(?:" + n + r")\b", "u" if n.isupper() else "iu")
                                                   for n in a["names"]]} for a in doc.get("acts", [])],
        "section": py_to_js(doc["section"], "iu"),
        "otherActs": py_to_js(doc["other_acts"]) if doc.get("other_acts") else None,
        "concepts": [{"rule": c["rule"], **py_to_js(c["regex"])} for c in doc.get("concepts", [])],
        "figures": [{"topic": f["topic"], **py_to_js(f["regex"])} for f in doc.get("figures", [])],
    }

def _d(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v

def _verification() -> dict[str, Any]:
    """The same generated status line as the README (`inforce verify --summary`)."""
    from .loader import verify_list, verify_summary
    from .paths import RULES_DIR
    items = verify_list(RULES_DIR)
    return {"verified": sum(i["verified"] for i in items), "total": len(items), "summary": verify_summary(RULES_DIR)}


def build_export(law_pack: str | Path) -> dict[str, Any]:
    with open_store(law_pack, read_only=True) as store:
        dates = [BEFORE_ALL] + [_d(r["d"]) for r in store.run("change_dates")]
        meta = store.run("pack_meta")

        rules = {}
        for row in store.run("all_rules"):
            at = []
            for d in dates:
                r = law.rule_status(store, row["id"], d)
                succ = r["successors"][0] if r["successors"] else None
                scale = r.get("scale")
                at.append({
                    "status": r["status"], "endedOn": _d(r["endedOn"]),
                    "successor": succ["text"] if succ else (law.scale_text(scale) if scale else None),
                    "successorRef": succ["id"] if succ else (scale["provision"] if scale else None),
                    "related": [x["text"] for x in r.get("related", [])],
                    "startUnknown": start_unknown(r["status"], r.get("startsOn")),
                })
            info = store.run("rule_info", id=row["id"])[0]
            rules[row["id"]] = {"notes": law.rule_notes(store, row["id"]),
                                "text": info["text"], "topic": info["topic"], "value": info["value"],
                                "unit": info["unit"], "verified": info["verified"] is True,
                                "provision": info["provision"], "source": info["source"], "at": at}

        acts = {}
        for row in store.run("all_instruments"):
            at = []
            for d in dates:
                i = law.instrument_status(store, row["akn"], d)
                at.append({"status": i["status"], "endedOn": _d(i["endedOn"]), "verified": i["statusVerified"] is True,
                           "startUnknown": start_unknown(i["status"], i["commencesOn"]),
                           "successor": i["repealedByTitle"], "successorRef": i["repealedBy"]})
            i0 = law.instrument_status(store, row["akn"], dates[-1])
            acts[row["short"] or row["akn"]] = {"akn": row["akn"], "title": row["title"], "source": i0["source"],
                                                "verified": i0["instrumentVerified"] is True, "at": at}

        provisions = {}
        for row in store.run("provisions_numbered"):
            at = []
            for d in dates:
                p = law.provision_status(store, row["akn"], d)
                at.append({"status": p["status"], "endedOn": _d(p["endedOn"]),
                           "startUnknown": start_unknown(p["status"], p["startsOn"]),
                           "successor": None, "successorRef": None})
            provisions[f"{row['short']}|{row['number']}"] = {"akn": row["akn"], "verified": row["verified"] is True,
                                                             "at": at}

    return {
        "format": 1,
        "generated": dt.date.today().isoformat(),
        "builtWith": "Built with Relate",
        "lawPack": {"file": "data/ng-tax-2026.rl", "buildHash": meta[0]["hash"] if meta else None},
        "dates": dates,
        "rules": rules, "acts": acts, "provisions": provisions,
        "patterns": js_patterns(),
        "unverified": sum(not r["verified"] for r in rules.values()),
        "verification": _verification(),
        "startUnknownNote": START_UNKNOWN,
        "disclaimer": DISCLAIMER,
    }

def write_export(law_pack: str | Path, out: str | Path) -> dict[str, Any]:
    data = build_export(law_pack)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
