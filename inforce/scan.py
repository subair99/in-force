"""`inforce scan`: link a repo's code and documents to the law they rest on.

1. Walk the repo (patterns/ng-paye.yaml `file_globs`).
2. Python files: module-level constants matched by `constants` patterns ENCODE rules;
   top-level functions that use them, importers and tests form USED_BY / TESTED_BY ripple edges.
   Documents, templates and answers: claims from the same patterns as `check`.
3. Copy the slice of the law pack those links touch into the project graph
   (one statement reads one graph), then write artifacts, claims and edges.
4. Statuses come from Cypher on the project graph: status_on / instrument_status for each
   law node, stale_artifacts for direct hits, ripple for what rests on them.

Writes <repo>/.inforce/project.rl. Nothing here decides law in Python.
"""
from __future__ import annotations

import ast
import datetime as dt
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from . import law
from .check import DISCLAIMER, resolve
from .cite_parser import extract
from .paths import PATTERNS_DIR
from .store import Store, open_store

PAYE_PATTERNS = PATTERNS_DIR / "ng-paye.yaml"
KIND_ORDER = ("test", "code", "answer", "template", "doc")
FOLLOW_IN = {"CONTAINS", "SETS", "REPEALS", "SAVES"}   # law closure: who sets / contains / ends / saves it
FOLLOW_OUT = {"REPLACED_BY", "FROM"}                   # law closure: what replaced it, where it came from


@cache
def load_paye_patterns(path: str | Path = PAYE_PATTERNS) -> dict[str, Any]:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for c in cfg.get("constants", []):
        c["_rx"] = re.compile(c["name_regex"])
    return cfg


# ---------------------------------------------------------------------------
# Findings (pure Python, no store)
# ---------------------------------------------------------------------------

@dataclass
class Findings:
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)  # id -> {id, path, symbol, kind, line}
    encodes: list[dict[str, Any]] = field(default_factory=list)          # {artifact, rule, line, pattern}
    claims: list[dict[str, Any]] = field(default_factory=list)           # {artifact, claim(Claim)}
    edges: set[tuple[str, str, str]] = field(default_factory=set)        # (source, target, type)

    def add_artifact(self, aid: str, path: str, kind: str, symbol: str | None = None, line: int | None = None):
        self.artifacts.setdefault(aid, {"id": aid, "path": path, "symbol": symbol, "kind": kind, "line": line})


def collect_files(root: Path, cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """(relative posix path, kind) for every file to scan, sorted."""
    globs = cfg.get("file_globs", {})
    ignored = {p for g in globs.get("ignore", []) for p in root.glob(g) if p.is_file()}
    out: dict[str, str] = {}
    for kind in KIND_ORDER:
        for g in globs.get(kind, []):
            for p in root.glob(g):
                if p.is_file() and p not in ignored:
                    out.setdefault(p.relative_to(root).as_posix(), kind)
    return sorted(out.items())


def _numbers(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, (list, tuple, set)):
        return [n for v in value for n in _numbers(v)]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    return []


def _close(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def match_constant(name: str, value: Any, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """The `constants` patterns this module-level constant matches."""
    hits = []
    for c in cfg.get("constants", []):
        if not c["_rx"].search(name):
            continue
        if "value_equals" in c:
            nums = _numbers(value)
            if not (len(nums) == 1 and _close(nums[0], float(c["value_equals"]))):
                continue
        if "value_contains" in c:
            nums = _numbers(value)
            if not all(any(_close(n, float(want)) for n in nums) for want in c["value_contains"]):
                continue
        hits.append(c)
    return hits


def _names_used(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | \
           {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


@dataclass
class PyModule:
    path: str
    kind: str
    symbols: dict[str, str] = field(default_factory=dict)       # name -> artifact id (functions, matched constants)
    functions: dict[str, set[str]] = field(default_factory=dict)  # function name -> names it uses
    imports: list[tuple[str, str]] = field(default_factory=list)  # (module dotted path, name)


def analyze_python(path: str, kind: str, src: str, cfg: dict[str, Any], f: Findings) -> PyModule | None:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    mod = PyModule(path, kind)
    for node in tree.body:
        if isinstance(node, (ast.ImportFrom,)) and node.module and node.level == 0:
            mod.imports += [(node.module, a.name) for a in node.names]
        if kind == "test":
            continue  # a test file is one artifact; its functions are not law-bearing symbols
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            try:
                value = ast.literal_eval(node.value) if node.value is not None else None
            except (ValueError, SyntaxError, TypeError):
                value = None
            for name in names:
                hits = match_constant(name, value, cfg)
                if hits:
                    aid = f"{path}::{name}"
                    f.add_artifact(aid, path, kind, name, node.lineno)
                    mod.symbols[name] = aid
                    for h in hits:
                        f.encodes.append({"artifact": aid, "rule": h["rule"], "line": node.lineno,
                                          "pattern": h["name_regex"]})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            aid = f"{path}::{node.name}"
            f.add_artifact(aid, path, kind, node.name, node.lineno)
            mod.symbols[node.name] = aid
            mod.functions[node.name] = _names_used(node)
    if kind == "test":
        f.add_artifact(path, path, kind, None, 1)
    # inside one module: a function using a constant or another function
    for fn, used in mod.functions.items():
        for name in used & set(mod.symbols):
            if name != fn:
                f.edges.add((mod.symbols[name], mod.symbols[fn], "USED_BY"))
    return mod


def _module_path(dotted: str, modules: dict[str, PyModule]) -> str | None:
    base = dotted.replace(".", "/")
    for cand in (f"{base}.py", f"{base}/__init__.py"):
        if cand in modules:
            return cand
    return None


def link_imports(modules: dict[str, PyModule], f: Findings) -> None:
    """`from a.b import name` -> (a/b.py::name)-[:USED_BY|TESTED_BY]->(user)."""
    for mod in modules.values():
        for dotted, name in mod.imports:
            src_path = _module_path(dotted, modules)
            if src_path is None:
                continue
            target = modules[src_path].symbols.get(name)
            if target is None:
                continue
            if mod.kind == "test":
                f.edges.add((target, mod.path, "TESTED_BY"))
                continue
            users = [mod.symbols[fn] for fn, used in mod.functions.items() if name in used]
            if not users:
                f.add_artifact(mod.path, mod.path, mod.kind)
                users = [mod.path]
            for u in users:
                f.edges.add((target, u, "USED_BY"))


def find(root: Path, cfg: dict[str, Any] | None = None) -> Findings:
    cfg = cfg or load_paye_patterns()
    f = Findings()
    modules: dict[str, PyModule] = {}
    for path, kind in collect_files(root, cfg):
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        if path.endswith(".py"):
            mod = analyze_python(path, kind, text, cfg, f)
            if mod:
                modules[path] = mod
        else:
            claims = extract(text)
            f.add_artifact(path, path, kind, None, 1)
            f.claims += [{"artifact": path, "claim": c} for c in claims]
    link_imports(modules, f)
    return f


# ---------------------------------------------------------------------------
# Law closure: the part of the law pack the repo depends on
# ---------------------------------------------------------------------------

def law_closure(seeds: set[str], rels: list[dict[str, Any]]) -> set[str]:
    keep = set(seeds)
    frontier = list(seeds)
    while frontier:
        k = frontier.pop()
        for r in rels:
            nxt = None
            if r["t"] == k and r["type"] in FOLLOW_IN:
                nxt = r["s"]
            elif r["s"] == k and r["type"] in FOLLOW_OUT:
                nxt = r["t"]
            if nxt and nxt not in keep:
                keep.add(nxt)
                frontier.append(nxt)
    return keep


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def _d(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def _resolve_claims(lp: Store, entries: list[dict[str, Any]], on: str) -> list[dict[str, Any]]:
    """Claim rows for write_claims: each claim with the law node it cites (None if not recognised)."""
    rows: list[dict[str, Any]] = []
    for entry in entries:
        c = entry["claim"]
        for item in resolve(lp, c, on):
            rows.append({
                "id": f"{entry['artifact']}#L{c.line}:{c.kind}:{item.ref or c.text}",
                "artifact": entry["artifact"], "text": item.claim, "kind": c.kind,
                "line": c.line, "target": item.ref if item.verdict != "NOT_RECOGNISED" else None,
            })
    return rows


def _law_slice(lp: Store, seeds: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The law nodes and relationships needed to decide the status of `seeds` (and their successors)."""
    nodes = lp.run("law_export_nodes")
    rels = lp.run("law_export_rels")
    keep = law_closure(seeds, rels)
    return [n for n in nodes if n["key"] in keep], [r for r in rels if r["s"] in keep and r["t"] in keep]


def _copy_law(ps: Store, node_rows: list[dict[str, Any]], rel_rows: list[dict[str, Any]]) -> None:
    if node_rows:
        ps.run("copy_law_nodes", rows=node_rows)
    if rel_rows:
        ps.run("copy_law_rels", rows=rel_rows)


def project_store_path(root: str | Path) -> Path:
    return Path(root).resolve() / ".inforce" / "project.rl"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def scan(root: str | Path, on: str, law_pack: str | Path, log=None) -> dict[str, Any]:
    root = Path(root).resolve()
    f = find(root)

    # Resolve document claims against the law pack, and export the law slice we need.
    with open_store(law_pack, read_only=True, log=log) as lp:
        claim_rows = _resolve_claims(lp, f.claims, on)
        seeds = {e["rule"] for e in f.encodes} | {r["target"] for r in claim_rows if r["target"]}
        node_rows, rel_rows = _law_slice(lp, seeds)
    known_rules = {n["key"] for n in node_rows if n["label"] == "Rule"}
    missing = sorted({e["rule"] for e in f.encodes} - known_rules)

    out = project_store_path(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open_store(out, log=log) as ps:
        ps.run_script("schema")
        with ps.transaction():
            ps.run("clear_scan")
            _copy_law(ps, node_rows, rel_rows)
            ps.run("write_artifacts", rows=list(f.artifacts.values()))
            if f.encodes:
                ps.run("write_encodes", rows=[e for e in f.encodes if e["rule"] in known_rules])
            if claim_rows:
                ps.run("write_claims", rows=claim_rows)
            if f.edges:
                ps.run("write_ripple", rows=[{"source": s, "target": t, "type": ty} for s, t, ty in sorted(f.edges)])
        report = evaluate(ps, on)
        ps.run("set_artifact_status", rows=[{"id": a["id"], "status": a["status"]} for a in report["artifacts"]],
               on=on, at=_now())
    report["store"] = str(out)
    report["warnings"] = [f"constant pattern names rule {r!r}, which is not in the law pack" for r in missing]
    return report


def record_answer(root: str | Path, answer_id: str, text: str, on: str, law_pack: str | Path,
                  log=None) -> dict[str, Any]:
    """Store an AI answer in a repo's project graph (artifact `agent/<answer_id>`, origin 'agent').

    This is the second writer next to `scan`: an agent records the answers it gave, so the
    project graph tracks which answers rest on repealed law, just like code. Re-recording the
    same id replaces it. Scans keep agent artifacts.
    """
    aid = f"agent/{answer_id}"
    entries = [{"artifact": aid, "claim": c} for c in extract(text)]
    with open_store(law_pack, read_only=True, log=log) as lp:
        claim_rows = _resolve_claims(lp, entries, on)
        node_rows, rel_rows = _law_slice(lp, {r["target"] for r in claim_rows if r["target"]})

    out = project_store_path(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open_store(out, log=log) as ps:
        ps.run_script("schema")
        with ps.transaction():
            ps.run("clear_artifact", id=aid)
            _copy_law(ps, node_rows, rel_rows)
            ps.run("write_artifacts", rows=[{"id": aid, "path": None, "symbol": None, "kind": "answer",
                                             "line": None, "origin": "agent"}])
            if claim_rows:
                ps.run("write_claims", rows=claim_rows)
        report = evaluate(ps, on)
        mine = next(a for a in report["artifacts"] if a["id"] == aid)
        ps.run("set_artifact_status", rows=[{"id": aid, "status": mine["status"]}], on=on, at=_now())
    return {"verdict": mine["status"], "on": on, "artifact": mine, "store": str(out),
            "claims": len(claim_rows), "disclaimer": DISCLAIMER}


def evaluate(store: Store, on: str) -> dict[str, Any]:
    """Status of every artifact in a project graph on `on`. Read-only; works on any project.rl."""
    # 1. status of each law node the repo rests on, by the same queries `check` uses
    targets: dict[str, dict[str, Any]] = {}
    for t in store.run("law_targets"):
        if t["label"] == "Rule":
            r = law.rule_status(store, t["key"], on)
            succ = r["successors"][0] if r and r["successors"] else None
            targets[t["key"]] = {"status": r["status"], "endedOn": r["endedOn"], "rule": r["text"],
                                 "successor": succ["text"] if succ else None,
                                 "successorRef": succ["id"] if succ else None, "path": r["path"]}
        elif t["label"] == "Instrument":
            i = law.instrument_status(store, t["key"], on)
            targets[t["key"]] = {"status": i["status"], "endedOn": i["endedOn"], "rule": i["title"],
                                 "successor": i["repealedByTitle"], "successorRef": i["repealedBy"],
                                 "path": i["path"]}
        elif t["label"] == "Provision":
            p = law.provision_status(store, t["key"], on)
            targets[t["key"]] = {"status": p["status"], "endedOn": p["endedOn"], "rule": t["key"],
                                 "successor": None, "successorRef": None, "path": [f"Provision {t['key']}"]}
    stale_keys = sorted(k for k, v in targets.items() if v["status"] == "REPEALED")

    # 2. artifacts that rest on repealed law directly, and what rests on them
    direct = {r["artifact"]: r for r in store.run("stale_artifacts", stale=stale_keys)} if stale_keys else {}
    ripple = {r["artifact"]: r["alsoCheck"] for r in store.run("ripple", ids=sorted(direct))} if direct else {}
    edges = store.run("ripple_edges")
    links = store.run("artifact_links")

    artifacts: dict[str, dict[str, Any]] = {}
    for row in links:
        a = artifacts.setdefault(row["artifact"], {
            "id": row["artifact"], "kind": row["kind"], "path": row["path"], "line": row["line"],
            "origin": row["origin"], "status": "CURRENT",
            "because": [], "via": [], "alsoCheck": [], "_suspect": False})
        if row["linked"] and (row["target"] is None or row["verified"] is not True):
            a["_suspect"] = True

    for aid, row in direct.items():
        a = artifacts[aid]
        a["status"] = "STALE"
        for b in row["because"]:
            t = targets.get(b["target"], {})
            a["because"].append({**b, "rule": t.get("rule"), "endedOn": _d(t.get("endedOn")),
                                 "successor": t.get("successor"), "successorRef": t.get("successorRef"),
                                 "path": t.get("path", [])})
        a["alsoCheck"] = sorted(ripple.get(aid, []))

    # 3. inheritance: anything that uses or tests a STALE artifact is STALE too (with the chain that says why)
    for src, rested in ripple.items():
        for aid in rested:
            a = artifacts.get(aid)
            if a and aid not in direct:
                a["status"] = "STALE"
                a["via"] = sorted(set(a["via"]) | {src})
    for a in artifacts.values():
        if a["status"] == "CURRENT" and a.pop("_suspect"):
            a["status"] = "SUSPECT"
        a.pop("_suspect", None)
        a["chain"] = _chain(a["id"], set(direct), edges) if a["via"] else []

    order = {"STALE": 0, "SUSPECT": 1, "CURRENT": 2}
    items = sorted(artifacts.values(), key=lambda a: (order[a["status"]], bool(a["via"]), a["id"]))
    verdict = "STALE" if any(a["status"] == "STALE" for a in items) else \
              "SUSPECT" if any(a["status"] == "SUSPECT" for a in items) else "CURRENT"
    return {
        "verdict": verdict, "on": on, "artifacts": items,
        "path": [" ".join(b["path"]) for a in items for b in a["because"] if b["path"]],
        "disclaimer": DISCLAIMER,
    }


def _chain(aid: str, direct: set[str], edges: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Shortest USED_BY/TESTED_BY chain from a directly stale artifact to `aid`: [{source, type, target}]."""
    back = {}
    for e in edges:
        back.setdefault(e["target"], []).append(e)
    frontier, seen = [(aid, [])], {aid}
    while frontier:
        nxt = []
        for node, steps in frontier:
            for e in back.get(node, []):
                step = steps + [{"source": e["source"], "type": e["type"], "target": node}]
                if e["source"] in direct:
                    return list(reversed(step))
                if e["source"] not in seen:
                    seen.add(e["source"])
                    nxt.append((e["source"], step))
        frontier = nxt
    return []
