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
import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import resources
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
    skipped: bool = False
    embedded: str | None = None


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


def _str(value: Any) -> str | None:
    """Section numbers and gazette pages are labels ("196", "A502"): keep them as text."""
    return None if value is None else str(value)


def provision_numbering(e: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """(number to show, gazetted page, note) for a provision.

    With `numbers:` per edition, the certified (current) number is shown; where the gazetted text
    numbers it differently, the note says so ("s.183(2) in the gazetted text"). A number known only
    from the gazetted text is shown with a note that the certified numbering is not yet checked.
    """
    nums = e.get("numbers") or {}
    if not nums:
        return _str(e.get("number")), _str(e.get("page")), None
    cert, gaz = nums.get("certified") or {}, nums.get("gazetted") or {}
    page = _str(gaz.get("page")) or _str(e.get("page"))
    if cert:
        note = (f"s.{gaz['number']} in the gazetted text"
                if gaz and str(gaz["number"]) != str(cert["number"]) else None)
        return str(cert["number"]), page, note
    return str(gaz["number"]), page, "gazetted text; certified numbering not yet checked"


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

    def src2(e: dict[str, Any], where: str) -> list[str] | None:
        """Optional secondary source(s): one id or a list (e.g. commentary kept next to the Act itself)."""
        sids = e.get("secondarySource")
        if sids is None:
            return None
        sids = [sids] if isinstance(sids, str) else list(sids)
        for sid in sids:
            if sid not in source_ids:
                w.append(f"{where}: secondary source {sid!r} is not in sources")
        return sids

    instruments: list[dict[str, Any]] = []
    versions: list[dict[str, Any]] = []   # bitemporal: which published version of an Act was on record when
    for e in data.get("instruments", []):
        where = f"instrument {e['akn']}"
        for ver in e.get("versions") or []:
            vwhere = f"{where} version {ver.get('version')}"
            versions.append({"key": f"{e['akn']}#{ver.get('version')}", "instrument": e["akn"],
                             "version": ver.get("version"),
                             "recordedAt": _date(ver.get("recordedAt"), f"{vwhere}.recordedAt", w),
                             "closedAt": _date(ver.get("closedAt"), f"{vwhere}.closedAt", w),
                             "verified": v(e) and ver.get("verified", True) is True,
                             "source": src(ver, vwhere), "note": ver.get("note")})
        instruments.append({
            "akn": e["akn"], "short": e.get("short"), "title": e.get("title"), "kind": e.get("kind"),
            "assentedOn": _date(e.get("assentedOn"), f"{where}.assentedOn", w),
            "commencesOn": _date(e.get("commencesOn"), f"{where}.commencesOn", w),
            "verified": v(e), "stub": False, "source": src(e, where), "secondarySource": src2(e, where),
            "page": _str(e.get("page")), "note": e.get("note"),
            "commencementSection": _str(e.get("commencementSection")),
        })
    inst_akns = {i["akn"] for i in instruments}

    version_keys = {v_["key"] for v_ in versions}
    numbered: list[dict[str, Any]] = []   # section number per published edition (gazetted, certified)
    provisions = []
    for e in data.get("provisions", []):
        where = f"provision {e['akn']}"
        inst = e.get("instrument")
        if inst not in inst_akns:
            raise BadReference(f"{where}: instrument {inst!r} is not defined")
        number, page, note = provision_numbering(e)
        for edition, d in (e.get("numbers") or {}).items():
            vkey = f"{inst}#{edition}"
            if vkey not in version_keys:
                raise BadReference(f"{where}: numbers.{edition} names no version of {inst}")
            numbered.append({"provision": e["akn"], "version": vkey, "number": str(d["number"]),
                             "page": _str(d.get("page")), "text": d.get("text"), "note": d.get("note")})
        provisions.append({
            "akn": e["akn"], "instrument": inst, "number": number, "numberNote": note,
            "summary": e.get("summary"), "note": e.get("note"),
            "validFrom": _date(e.get("validFrom"), f"{where}.validFrom", w),
            "validTo": _date(e.get("validTo"), f"{where}.validTo", w),
            "recordedAt": _date(e.get("recordedAt"), f"{where}.recordedAt", w),
            "closedAt": _date(e.get("closedAt"), f"{where}.closedAt", w),
            "verified": v(e), "stub": False, "source": src(e, where),
            "page": page, "secondarySource": src2(e, where),
        })
    prov_akns = {p["akn"] for p in provisions}
    commencing = {i["akn"] for i in instruments if i["commencesOn"]}
    for p in provisions:
        if p["instrument"] in commencing and not p["validFrom"]:
            w.append(f"provision {p['akn']}: no validFrom; its start falls back to {p['instrument']}'s "
                     "commencement date. Set validFrom explicitly")

    def stub_provision(akn: str, why: str) -> None:
        # Referenced but not defined: create an empty, unverified placeholder.
        # No dates, no instrument, no summary: nothing is invented.
        provisions.append({"akn": akn, "instrument": None, "number": None, "numberNote": None, "summary": None,
                           "note": None,
                           "validFrom": None, "validTo": None, "recordedAt": None, "closedAt": None,
                           "verified": False, "stub": True, "source": None, "page": None, "secondarySource": None})
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
            "page": _str(e.get("page")), "secondarySource": src2(e, where),
        })
    rule_ids = {r["id"] for r in rules}
    # A rule may also be set by further provisions (e.g. a rate stated in two sections); the
    # `provision` field stays the primary one, the others are SETS marked secondary.
    also_sets = []
    for e in data.get("rules", []):
        for akn in e.get("alsoProvisions") or []:
            if akn not in prov_akns:
                raise BadReference(f"rule {e['id']}: alsoProvisions names undefined provision {akn!r}")
            also_sets.append({"rule": e["id"], "provision": akn})

    repeals = []
    for e in data.get("repeals", []):
        where = f"repeal {e['by']} -> {e['target']}"
        if e["by"] not in inst_akns:
            raise BadReference(f"{where}: repealing instrument is not defined")
        if e["target"] not in inst_akns | prov_akns:
            raise BadReference(f"{where}: target is not a defined instrument or provision")
        bp = e.get("byProvision")
        if bp is not None and bp not in prov_akns:
            raise BadReference(f"{where}: byProvision {bp!r} is not defined")
        bp_row = next((p for p in provisions if p["akn"] == bp), None)
        repeals.append({"by": e["by"], "target": e["target"], "on": _date(e.get("on"), f"{where}.on", w),
                        "byProvision": bp,
                        "section": bp_row["number"] if bp_row else _str(e.get("section")),
                        "page": _str(e.get("page")),
                        "verified": v(e), "source": src(e, where), "secondarySource": src2(e, where)})

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
                        "note": e.get("note"), "verified": v(e), "source": src(e, where),
                        "page": _str(e.get("page")), "secondarySource": src2(e, where)})

    sources = [{"id": s["id"], "url": s["url"], "kind": s.get("kind"), "title": s.get("title"),
                "citation": s.get("citation"), "note": s.get("note")}
               for s in data.get("sources", [])]

    return {"source": sources, "instrument": instruments, "version": versions, "provision": provisions,
            "numbered": numbered, "rule": rules,
            "also_sets": also_sets, "repeal": repeals, "replacement": replacements, "succession": successions, "related": related,
            "grant": grants, "saving": savings}


# Order matters: nodes before the relationships that MATCH them.
LOAD_ORDER = ("source", "instrument", "version", "provision", "numbered", "rule", "also_sets", "repeal", "replacement", "succession", "related",
              "grant", "saving")


def build_hash(rules_dir: str | Path) -> str:
    """sha256 of everything that decides the pack's law content: the rule YAML, this loader and its queries.
    (Which embedding model was used is stored separately, so a machine without the model can still
    recognise an up-to-date pack and leave it alone.)"""
    h = hashlib.sha256()
    queries = resources.files("inforce") / "queries"
    parts = sorted(Path(rules_dir).glob("*.yaml")) + [Path(__file__)]
    # Line endings are normalised: git on Windows checks text out with CRLF, and the same content
    # must give the same hash there (otherwise `make demo` would rebuild the committed pack).
    def norm(b: bytes) -> bytes:
        return b.replace(b"\r\n", b"\n")
    for p in parts:
        h.update(p.name.encode() + b"\0" + norm(p.read_bytes()))
    for name in sorted(n.name for n in queries.iterdir() if n.name == "schema.cypher" or n.name.startswith("load_")):
        h.update(name.encode() + b"\0" + norm((queries / name).read_bytes()))
    return h.hexdigest()


def pack_meta(out_path: str | Path) -> dict[str, Any] | None:
    """{hash, embedModel} stored in an existing pack, or None."""
    if not Path(out_path).exists():
        return None
    try:
        with open_store(out_path, read_only=True) as s:
            rows = s.run("pack_meta")
    except Exception:  # noqa: BLE001 - unreadable or old pack: rebuild it
        return None
    return rows[0] if rows else None


def load(
    rules_dir: str | Path,
    out_path: str | Path,
    allow_unverified: bool = False,
    log: Callable[[str], None] | None = None,
    force: bool = False,
    embed: bool = True,
) -> LoadReport:
    """Rebuild `out_path` from the YAML in `rules_dir`. Returns a LoadReport.

    Skips the rebuild (report.skipped = True) when the pack was built from the same YAML,
    loader and queries, unless `force`. A rebuilt .rl differs in bytes even with the same
    content, so skipping keeps a fresh clone's committed pack untouched by `make demo`.
    """
    out_path = Path(out_path)
    report = LoadReport(path=out_path)
    data = read_yaml(Path(rules_dir))

    report.unverified = unverified_entries(data)
    if report.unverified and not allow_unverified:
        raise UnverifiedLaw(report.unverified)

    rows = build_rows(data, report)
    digest = build_hash(rules_dir)
    meta = pack_meta(out_path)
    if not force and meta and meta["hash"] == digest and (meta["embedModel"] or not embed):
        with open_store(out_path, read_only=True, log=log) as store:
            report.counts = {r["label"]: r["n"] for r in store.run("law_counts")}
        report.skipped = True
        report.embedded = meta["embedModel"]
        return report

    embed_model = None
    if embed and rows["rule"]:
        from . import embed as emb
        vectors = emb.embed([emb.rule_text(r) for r in rows["rule"]])
        if vectors is None:
            report.warnings.append(f"embedding model {emb.MODEL} not available (offline or not cached): "
                                   "rules loaded without embeddings; `ask` will use full-text only")
        else:
            embed_model = emb.MODEL
            for r, v in zip(rows["rule"], vectors, strict=True):
                r["embedding"] = v
    for r in rows["rule"]:
        r.setdefault("embedding", None)
    report.embedded = embed_model

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
                store.run("load_meta", hash=digest, model=embed_model)
            report.counts = {r["label"]: r["n"] for r in store.run("law_counts")}
        os.replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return report


def verify_list(rules_dir: str | Path) -> list[dict[str, Any]]:
    """Every law entry, for the human check against the Act: what it says, its source and verified flag.
    Read from the YAML (the file the human edits), with the file and line of each entry."""
    data = read_yaml(Path(rules_dir))
    def show_source(sid: str | None) -> str | None:
        """The source URL, or its citation when the URL is still a placeholder."""
        s = srcs.get(sid)
        if s is None:
            return sid
        return s["url"] if not str(s["url"]).startswith("TODO") else (s.get("citation") or s["url"])

    def source_label(sid: str | None) -> str | None:
        s = srcs.get(sid)
        return (s.get("title") or s.get("citation")) if s else None

    def secondaries(e: dict[str, Any]) -> list[str]:
        sids = e.get("secondarySource")
        sids = [] if sids is None else [sids] if isinstance(sids, str) else list(sids)
        return [show_source(x) for x in sids]

    srcs = {s["id"]: s for s in data.get("sources", [])}
    lines: dict[str, list[str]] = {f.name: f.read_text(encoding="utf-8").splitlines()
                                   for f in sorted(Path(rules_dir).glob("*.yaml"))}

    def where(needles: list[str]) -> str:
        """file:line of the first non-comment line containing every needle."""
        for name, ls in lines.items():
            for n, line in enumerate(ls, 1):
                if not line.lstrip().startswith("#") and all(x in line for x in needles):
                    return f"{name}:{n}"
        return ""

    pairs = {"repeals": ("by", "target"), "replacements": ("old", "new"), "successions": ("old", "new"),
             "related": ("rule", "related"), "savings": ("saver", "saves")}

    out = []
    for sec in LAW_SECTIONS:
        for e in data.get(sec, []):
            label = _label(sec, e)
            if sec in pairs:
                a, b = pairs[sec]
                needles = [f"{a}: {e[a]}", f"{b}: {e[b]}"]
            elif e.get("akn"):
                needles = [f"akn: {e['akn']}"]
            else:
                needles = [f"id: {e['id']}"]
            what = e.get("text") or e.get("summary") or e.get("title") or e.get("note") or ""
            if sec == "repeals":
                what = f"repealed on {e.get('on')}" + (f" under section {e['section']}" if e.get("section") else "")
            if e.get("value") is not None:
                what += f" (value {e['value']} {e.get('unit') or ''})".rstrip()
            out.append({"kind": sec[:-1] if sec != "related" else "related", "entry": label.split(" ", 1)[1],
                        "what": what, "source": show_source(e.get("source")), "sourceLabel": source_label(e.get("source")),
                        "page": None if e.get("page") is None else str(e["page"]),
                        "secondarySources": secondaries(e),
                        "verified": e.get("verified") is True, "where": where(needles)})
    return out


STATUS_START, STATUS_END = "<!-- inforce:verify-status -->", "<!-- /inforce:verify-status -->"


def verify_summary(rules_dir: str | Path) -> str:
    """The one-line verification status, generated from the YAML (never written by hand)."""
    items = verify_list(rules_dir)
    n = sum(i["verified"] for i in items)
    return (f"Each rule links to its source; verification against the Act's text is in progress "
            f"({n} of {len(items)} law entries verified).")


def update_status_block(text: str, summary: str) -> str:
    """Replace the content between the verify-status markers with `summary`."""
    a, b = text.find(STATUS_START), text.find(STATUS_END)
    if a == -1 or b == -1 or b < a:
        raise ValueError(f"missing {STATUS_START} ... {STATUS_END} markers")
    return text[:a + len(STATUS_START)] + summary + text[b:]
