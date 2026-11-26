"""Truth questions about the law pack, each answered by a Cypher query.

Statuses (SPEC §3): IN_FORCE, REPEALED, SAVED, NOT_YET. A rule takes the status
of the provision that SETS it. Every function takes an open Store, so a command
opens the store once, asks many questions, and closes it.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from .store import Store

LIVE = ("IN_FORCE", "SAVED")


def _iso(on: str | dt.date) -> str:
    return on.isoformat() if isinstance(on, dt.date) else str(on)


def provision_status(store: Store, akn: str, on: str | dt.date) -> dict[str, Any] | None:
    rows = store.run("status_on", akn=akn, on=_iso(on))
    return rows[0] if rows else None


def instrument_status(store: Store, ref: str, on: str | dt.date) -> dict[str, Any] | None:
    """Status of a whole Act, by akn or short name (e.g. 'PITA')."""
    rows = store.run("instrument_status", ref=ref, on=_iso(on))
    if not rows:
        return None
    row = rows[0]
    row["path"] = _instrument_path(row)
    return row


def provision_by_number(store: Store, ref: str, number: str) -> str | None:
    row = provision_lookup(store, ref, number)
    return row["akn"] if row else None


def provision_lookup(store: Store, ref: str, number: str) -> dict[str, Any] | None:
    """A provision by its section number in any edition: {akn, current, note}."""
    rows = store.run("provision_by_number", ref=ref, number=str(number))
    return rows[0] if rows else None


def rules_by_value(store: Store, topic: str, value: float) -> list[str]:
    return [r["id"] for r in store.run("rules_by_value", topic=topic, value=float(value))]


def rule_status(store: Store, rule_id: str, on: str | dt.date) -> dict[str, Any] | None:
    """A rule's status on `on`, why (proof path), and what replaced it.

    `successors` holds at most one rule: the furthest rule down the
    REPLACED_BY chain that is live (in force or saved) on `on`. If none is
    live yet, the nearest replacement is shown with its own status.
    """
    rows = store.run("rule_info", id=rule_id)
    if not rows:
        return None
    rule = rows[0]
    st = provision_status(store, rule["provision"], on) if rule["provision"] else None
    rule["status"] = st["status"] if st else "UNKNOWN"
    rule["endedOn"] = st["endedOn"] if st else None
    rule["repealedBy"] = st["repealedBy"] if st else None
    rule["savers"] = st["savers"] if st else []
    rule["verified"] = rule["verified"] is True
    rule["path"] = _rule_path(rule, st)

    rule["notes"] = rule_notes(store, rule_id)
    chain = store.run("rule_successors", id=rule_id)
    for c in chain:
        cs = provision_status(store, c["provision"], on) if c["provision"] else None
        c["status"] = cs["status"] if cs else "UNKNOWN"
        c["verified"] = c["verified"] is True
        c["notes"] = rule_notes(store, c["id"])
    live = [c for c in chain if c["status"] in LIVE]
    if live:
        rule["successors"] = [max(live, key=lambda c: c["depth"])]
    elif chain:
        rule["successors"] = [chain[0]]
    else:
        rule["successors"] = []

    # The provision that set this rule was replaced as a whole (SUCCEEDED_BY): the new scale.
    scale_rows = store.run("rule_scale", id=rule_id)
    rule["scale"] = None
    if scale_rows:
        head = scale_rows[0]
        st_new = provision_status(store, head["provision"], on)
        rule["scale"] = {
            "provision": head["provision"], "short": head["short"], "number": head["number"],
            "note": head["note"], "verified": head["verified"] is True,
            "status": st_new["status"] if st_new else "UNKNOWN",
            "rules": [{"id": r["id"], "text": r["text"], "value": r["value"], "verified": r["ruleVerified"] is True}
                      for r in scale_rows],
        }
        rule["path"].append(f"-SUCCEEDED_BY-> Provision {head['provision']}")
    # Related rules: read together, never a successor.
    rule["related"] = store.run("rule_related", id=rule_id)
    return rule


def scale_text(scale: dict[str, Any]) -> str:
    """'NTA s. 58 (whole scale): PIT: first ... · PIT: next ...'"""
    where = f"{scale['short'] or ''} s. {scale['number']}".strip() if scale.get("number") else scale["provision"]
    return f"{where} (whole scale): " + " · ".join(r["text"] for r in scale["rules"])


def rule_notes(store: Store, rule_id: str) -> list[str]:
    """Notes on the provisions that set a rule, e.g. 's.56: Proviso: the 30% rate is to be reduced ...'."""
    return [f"s.{r['number']}: {r['note']}" if r["number"] else r["note"]
            for r in store.run("rule_notes", id=rule_id)]


def fallout(store: Store, instrument: str, on: str | dt.date) -> list[dict[str, Any]]:
    """Dependents (grants, subsidiary instruments) of an Act: FELL, SAVED or STANDS on `on`."""
    return store.run("fallout", repealed=instrument, on=_iso(on))


# ---------------------------------------------------------------------------
# Proof paths: the graph walk behind a verdict, as readable steps
# ---------------------------------------------------------------------------

def _rule_path(rule: dict[str, Any], st: dict[str, Any] | None) -> list[str]:
    path = [f"Rule {rule['id']}"]
    if rule.get("provision"):
        path.append(f"<-SETS- Provision {rule['provision']}")
    if rule.get("instrument"):
        path.append(f"<-CONTAINS- Instrument {rule.get('short') or rule['instrument']}")
    if st and st.get("endedOn"):
        if st.get("repealedBy"):
            path.append(f"<-REPEALS {st['endedOn']}- Instrument {st.get('repealedByShort') or st['repealedBy']}")
        else:
            path.append(f"(validTo {st['endedOn']})")
    for s in (st or {}).get("savers") or []:
        path.append(f"<-SAVES- Provision {s}")
    return path


def _instrument_path(row: dict[str, Any]) -> list[str]:
    path = [f"Instrument {row.get('short') or row['akn']}"]
    if row.get("repealedBy"):
        path.append(f"<-REPEALS {row['endedOn']}- Instrument {row.get('repealedByShort') or row['repealedBy']}")
    return path


def keystones(store: Store, on: str | dt.date) -> list[dict[str, Any]]:
    """Rules a project graph rests on most (direct + downstream artifacts), with each rule's status on `on`."""
    rows = store.run("keystones")
    for r in rows:
        st = rule_status(store, r["rule"], on)
        r["status"] = st["status"] if st else "UNKNOWN"
        r["verified"] = bool(st and st["verified"])
    return rows


def diff_known_on(store: Store, d1: str | dt.date, d2: str | dt.date) -> dict[str, Any]:
    """What was on record on d1 versus d2 (bitemporal): each Act's version, and provisions that carry
    recordedAt/closedAt. Unknown recording dates are flagged, never assumed."""
    d1, d2 = _iso(d1), _iso(d2)
    v1 = store.run("known_versions", d=d1)
    v2 = store.run("known_versions", d=d2)
    acts: dict[str, dict[str, Any]] = {}
    for tag, rows in (("d1", v1), ("d2", v2)):
        for r in rows:
            a = acts.setdefault(r["akn"], {"akn": r["akn"], "short": r["short"], "d1": [], "d2": []})
            a[tag].append({"version": r["version"], "recordedAt": r["recordedAt"],
                           "startUnknown": r["startUnknown"], "verified": r["verified"] is True})
    for a in acts.values():
        a["changed"] = sorted(x["version"] for x in a["d1"]) != sorted(x["version"] for x in a["d2"])
    # Section numbers that differ between the editions on record on d1 and d2 (e.g. gazetted -> certified).
    n1 = {(r["akn"]): r for r in store.run("known_numbers", d=d1)}
    n2 = {(r["akn"]): r for r in store.run("known_numbers", d=d2)}
    numbering = [{"akn": k, "summary": n1[k]["summary"], "act": n1[k]["short"], "note": n1[k]["note"],
                  "d1": {"version": n1[k]["version"], "number": n1[k]["number"], "page": n1[k]["page"]},
                  "d2": {"version": n2[k]["version"], "number": n2[k]["number"], "page": n2[k]["page"]}}
                 for k in sorted(set(n1) & set(n2)) if n1[k]["number"] != n2[k]["number"]]
    unchecked = sorted(k for k in set(n1) ^ set(n2))  # numbered in only one of the two editions
    p1 = {r["akn"]: r for r in store.run("known_provisions", d=d1)}
    p2 = {r["akn"]: r for r in store.run("known_provisions", d=d2)}
    provisions = [{"akn": k, "summary": p1[k]["summary"], "d1": p1[k]["known"], "d2": p2[k]["known"]}
                  for k in sorted(p1) if p1[k]["known"] != p2[k]["known"]]
    return {"d1": d1, "d2": d2, "acts": sorted(acts.values(), key=lambda a: a["akn"]),
            "numbering": numbering, "numberingUnchecked": unchecked,
            "provisions": provisions, "provisionsWithRecordDates": len(p1)}
