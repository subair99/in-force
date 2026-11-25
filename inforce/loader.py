"""Build the law pack (`data/ng-tax-2026.rl`) from `data/rules/*.yaml`.

Rules of the loader:
- It never changes a value. YAML in, graph out. Anything it cannot use
  (a `TODO` date, a reference to an entry that does not exist) is reported
  as a warning and left unset or stubbed, never guessed.
- Every law entry (instrument, provision, rule, repeal, replacement, grant,
  saving) whose `verified` is not `true` is unverified. Missing counts as
  false. Without `allow_unverified` the load refuses and lists them.
- The store is rebuilt from scratch into a temp file in the same directory
  and moved over the old one, so removed YAML entries do not linger.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .store import open_store

LAW_SECTIONS = ("instruments", "provisions", "rules", "repeals", "replacements", "successions", "related",
                "grants", "savings")


class UnverifiedLaw(RuntimeError):
    """Raised when the YAML holds unverified entries and --allow-unverified was not given."""

    def __init__(self, entries: list[str]):
        self.entries = entries
        super().__init__(f"{len(entries)} unverified law entries; pass --allow-unverified to load them anyway")


class BadReference(ValueError):
    """A repeal, saving or replacement points at something that does not exist."""


@dataclass
class LoadReport:
    path: Path
    counts: dict[str, int] = field(default_factory=dict)
    unverified: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stubs: list[str] = field(default_factory=list)


class _Yaml12BoolLoader(yaml.SafeLoader):
    """SafeLoader where only true/false are booleans.

    PyYAML follows YAML 1.1, where `on`, `off`, `yes` and `no` are booleans. Our
    repeals use the key `on:`, which would silently become `True` and lose
    every repeal date.
    """


_Yaml12BoolLoader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Yaml12BoolLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


def read_yaml(rules_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Merge every *.yaml under rules_dir into one dict of lists."""
    merged: dict[str, list[dict[str, Any]]] = {}
    files = sorted(Path(rules_dir).glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"no *.yaml files in {rules_dir}")
    for f in files:
        doc = yaml.load(f.read_text(encoding="utf-8"), Loader=_Yaml12BoolLoader) or {}
        for key, items in doc.items():
            merged.setdefault(key, []).extend(items or [])
    return merged


def _label(section: str, e: dict[str, Any]) -> str:
    key = e.get("akn") or e.get("id") or (
        f"{e.get('by') or e.get('old') or e.get('saver') or e.get('rule')} -> "
        f"{e.get('target') or e.get('new') or e.get('saves') or e.get('related')}")
    return f"{section[:-1]} {key}"


def unverified_entries(data: dict[str, list[dict[str, Any]]]) -> list[str]:
    return [_label(sec, e) for sec in LAW_SECTIONS for e in data.get(sec, []) if e.get("verified") is not True]


def _date(value: Any, where: str, warnings: list[str]) -> str | None:
    """ISO string for a YAML date, None for null. Anything else is warned about and left unset."""
    if value is None:
        return None
    if isinstance(value, dt.date):
        return value.isoformat()
    warnings.append(f"{where}: {value!r} is not a date; left unset")
    return None


def build_rows(data: dict[str, list[dict[str, Any]]], report: LoadReport) -> dict[str, list[dict[str, Any]]]:
    """Turn YAML entries into parameter rows for the load_*.cypher queries."""
    w = report.warnings
    v = lambda e: e.get("verified") is True

    source_ids = {s["id"] for s in data.get("sources", [])}

    def src(e: dict[str, Any], where: str) -> str | None:
        sid = e.get("source")
        if sid is not None and sid not in source_ids:
            w.append(f"{where}: source {sid!r} is not in sources; no FROM link")
        return sid

    instruments = []
    for e in data.get("instruments", []):
        where = f"instrument {e['akn']}"
        if e.get("versions"):
            w.append(f"{where}: versions (recordedAt/closedAt) not loaded yet; needed for `diff --known-on` (P1)")
        instruments.append({
            "akn": e["akn"], "short": e.get("short"), "title": e.get("title"), "kind": e.get("kind"),
            "assentedOn": _date(e.get("assentedOn"), f"{where}.assentedOn", w),
            "commencesOn": _date(e.get("commencesOn"), f"{where}.commencesOn", w),
            "verified": v(e), "stub": False, "source": src(e, where),
        })
    inst_akns = {i["akn"] for i in instruments}

    provisions = []
    for e in data.get("provisions", []):
        where = f"provision {e['akn']}"
        inst = e.get("instrument")
        if inst not in inst_akns:
            raise BadReference(f"{where}: instrument {inst!r} is not defined")
        provisions.append({
            "akn": e["akn"], "instrument": inst,
            "number": None if e.get("number") is None else str(e["number"]),
            "summary": e.get("summary"),
            "validFrom": _date(e.get("validFrom"), f"{where}.validFrom", w),
            "validTo": _date(e.get("validTo"), f"{where}.validTo", w),
            "verified": v(e), "stub": False, "source": src(e, where),
        })
    prov_akns = {p["akn"] for p in provisions}

    def stub_provision(akn: str, why: str) -> None:
        # Referenced but not defined: create an empty, unverified placeholder.
        # No dates, no instrument, no summary: nothing is invented.
        provisions.append({"akn": akn, "instrument": None, "number": None, "summary": None,
                           "validFrom": None, "validTo": None, "verified": False, "stub": True, "source": None})
        prov_akns.add(akn)
        report.stubs.append(f"provision {akn} (referenced by {why})")

    rules = []
    for e in data.get("rules", []):
        where = f"rule {e['id']}"
        if e.get("provision") not in prov_akns:
            stub_provision(e["provision"], where)
        rules.append({
            "id": e["id"], "provision": e["provision"], "text": e.get("text"), "topic": e.get("topic"),
            "value": e.get("value"), "unit": e.get("unit"), "verified": v(e), "source": src(e, where),
        })
    rule_ids = {r["id"] for r in rules}

    repeals = []
    for e in data.get("repeals", []):
        where = f"repeal {e['by']} -> {e['target']}"
        if e["by"] not in inst_akns:
            raise BadReference(f"{where}: repealing instrument is not defined")
        if e["target"] not in inst_akns | prov_akns:
            raise BadReference(f"{where}: target is not a defined instrument or provision")
        repeals.append({"by": e["by"], "target": e["target"], "on": _date(e.get("on"), f"{where}.on", w),
                        "verified": v(e), "source": src(e, where)})

    replacements = []
    for e in data.get("replacements", []):
        for k in ("old", "new"):
            if e[k] not in rule_ids:
                raise BadReference(f"replacement {e['old']} -> {e['new']}: rule {e[k]!r} is not defined")
        replacements.append({"old": e["old"], "new": e["new"], "verified": v(e)})

    successions = []
    for e in data.get("successions", []):
        where = f"succession {e['old']} -> {e['new']}"
        for k in ("old", "new"):
            if e[k] not in prov_akns:
                raise BadReference(f"{where}: provision {e[k]!r} is not defined")
        successions.append({"old": e["old"], "new": e["new"], "note": e.get("note"), "verified": v(e),
                            "source": src(e, where)})

    related = []
    for e in data.get("related", []):
        for k in ("rule", "related"):
            if e[k] not in rule_ids:
                raise BadReference(f"related {e['rule']} -> {e['related']}: rule {e[k]!r} is not defined")
        related.append({"rule": e["rule"], "related": e["related"], "note": e.get("note"), "verified": v(e)})

    grants = []
    for e in data.get("grants", []):
        where = f"grant {e['id']}"
        gu = e.get("grantedUnder")
        if gu not in inst_akns | prov_akns:  # a grant may rest on a whole Act or one provision
            stub_provision(gu, where)
        grants.append({"id": e["id"], "title": e.get("title"), "grantedUnder": gu, "verified": v(e)})
    grant_ids = {g["id"] for g in grants}

    savings = []
    for e in data.get("savings", []):
        where = f"saving {e['saver']} -> {e['saves']}"
        if e["saver"] not in prov_akns:
            raise BadReference(f"{where}: saving provision is not defined")
        if e["saves"] not in grant_ids | prov_akns:
            raise BadReference(f"{where}: target is not a defined grant or provision")
        savings.append({"saver": e["saver"], "saves": e["saves"],
                        "until": _date(e.get("until"), f"{where}.until", w),
                        "note": e.get("note"), "verified": v(e), "source": src(e, where)})

    sources = [{"id": s["id"], "url": s["url"], "kind": s.get("kind"), "title": s.get("title")}
               for s in data.get("sources", [])]

    return {"source": sources, "instrument": instruments, "provision": provisions, "rule": rules,
            "repeal": repeals, "replacement": replacements, "succession": successions, "related": related,
            "grant": grants, "saving": savings}


# Order matters: nodes before the relationships that MATCH them.
LOAD_ORDER = ("source", "instrument", "provision", "rule", "repeal", "replacement", "succession", "related",
              "grant", "saving")


def load(
    rules_dir: str | Path,
    out_path: str | Path,
    allow_unverified: bool = False,
    log: Callable[[str], None] | None = None,
) -> LoadReport:
    """Rebuild `out_path` from the YAML in `rules_dir`. Returns a LoadReport."""
    out_path = Path(out_path)
    report = LoadReport(path=out_path)
    data = read_yaml(Path(rules_dir))

    report.unverified = unverified_entries(data)
    if report.unverified and not allow_unverified:
        raise UnverifiedLaw(report.unverified)

    rows = build_rows(data, report)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.stem + ".building.rl")
    if tmp.exists():
        tmp.unlink()
    try:
        with open_store(tmp, log=log) as store:
            store.run_script("schema")
            with store.transaction():
                for kind in LOAD_ORDER:
                    if rows[kind]:
                        store.run(f"load_{kind}", rows=rows[kind])
            report.counts = {r["label"]: r["n"] for r in store.run("law_counts")}
        os.replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return report
