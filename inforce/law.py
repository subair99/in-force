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
    rows = store.run("provision_by_number", ref=ref, number=str(number))
    return rows[0]["akn"] if rows else None


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

    chain = store.run("rule_successors", id=rule_id)
    for c in chain:
        cs = provision_status(store, c["provision"], on) if c["provision"] else None
        c["status"] = cs["status"] if cs else "UNKNOWN"
        c["verified"] = c["verified"] is True
    live = [c for c in chain if c["status"] in LIVE]
    if live:
        rule["successors"] = [max(live, key=lambda c: c["depth"])]
    elif chain:
        rule["successors"] = [chain[0]]
    else:
        rule["successors"] = []
    return rule


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
