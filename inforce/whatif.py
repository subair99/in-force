"""`inforce whatif repeal`: what falls if a provision or Act were repealed on a date?

The hypothetical repeal is written inside a transaction, measured with the same status
queries as every other command, and rolled back. The command reports node and
relationship counts and a content fingerprint before, during and after, to show the
store is unchanged.

By default it runs on temporary copies of the stores: even a rolled-back writable open
rewrites a .rl file's bytes (same content), and the committed stores should stay as they
are. Pass in_place=True to run on the stores themselves.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from . import law
from .check import DISCLAIMER
from .scan import evaluate, project_store_path
from .store import Store, open_store

WHATIF_KEY = "whatif/hypothetical-repeal"


def fingerprint(store: Store) -> dict[str, Any]:
    """Counts plus a sha256 over every node (labels, properties) and relationship."""
    nodes = store.run("fingerprint_nodes")
    rels = store.run("fingerprint_rels")

    def norm(v):
        return json.dumps(v, sort_keys=True, default=str)
    h = hashlib.sha256()
    for line in sorted(norm(n) for n in nodes) + sorted(norm(r) for r in rels):
        h.update(line.encode())
    return {"nodes": len(nodes), "rels": len(rels), "sha256": h.hexdigest()[:16]}


def _law_snapshot(store: Store, on: str) -> dict[str, str]:
    """Status of every rule, Act and dependent (grant) on `on`, keyed for comparison."""
    snap: dict[str, str] = {}
    for r in store.run("all_rules"):
        st = law.rule_status(store, r["id"], on)
        snap[f"Rule {r['id']}|{r['text']}"] = st["status"]
    for i in store.run("all_instruments"):
        st = law.instrument_status(store, i["akn"], on)
        snap[f"Act {i['short'] or i['akn']}|{i['title'] or ''}"] = st["status"]
        for dep in law.fallout(store, i["akn"], on):
            snap[f"Grant {dep['id'] or dep['dependent']}|{dep['dependent']}"] = dep["verdict"]
    return snap


def _changes(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
    out = []
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            kind_id, _, label = k.partition("|")
            kind, _, ident = kind_id.partition(" ")
            out.append({"kind": kind, "id": ident, "label": label,
                        "before": before.get(k, "-"), "after": after.get(k, "-")})
    return out


def _apply_repeal(store: Store, target: str, on: str) -> bool:
    rows = store.run("whatif_repeal", target=target, on=on, key=WHATIF_KEY)
    return bool(rows)


def _working_copy(path: Path, stack: ExitStack, in_place: bool) -> Path:
    if in_place:
        return path
    tmp = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inforce-whatif-")))
    dst = tmp / path.name
    shutil.copy2(path, dst)
    return dst


def _run(store_path: Path, target: str, on: str, measure) -> dict[str, Any]:
    with open_store(store_path) as store:
        fp_before = fingerprint(store)
        before = measure(store)
        with store.rollback_only():
            found = _apply_repeal(store, target, on)
            fp_during = fingerprint(store)
            after = measure(store) if found else before
        fp_after = fingerprint(store)
    return {"found": found, "before": before, "after": after,
            "counts": {"before": fp_before, "during": fp_during, "after": fp_after},
            "unchanged": fp_before == fp_after}


def whatif_repeal(target: str, on: str, law_pack: str | Path, repo: str | Path | None = None,
                  in_place: bool = False) -> dict[str, Any]:
    """Hypothetically repeal `target` (provision akn, Act akn or Act short name) on `on`."""
    with ExitStack() as stack:
        lp = _working_copy(Path(law_pack), stack, in_place)
        law_run = _run(lp, target, on, lambda s: _law_snapshot(s, on))
        result: dict[str, Any] = {
            "target": target, "on": on, "inPlace": in_place,
            "law": {"found": law_run["found"], "changes": _changes(law_run["before"], law_run["after"]),
                    "counts": law_run["counts"], "unchanged": law_run["unchanged"]},
            "repo": None, "disclaimer": DISCLAIMER,
        }
        if repo is not None:
            ps = project_store_path(repo)
            if not ps.exists():
                raise FileNotFoundError(f"{ps} not found; run `inforce scan {repo}` first")
            pp = _working_copy(ps, stack, in_place)

            def measure(s: Store) -> dict[str, str]:
                return {f"Artifact {a['id']}|{a['kind']}": a["status"] for a in evaluate(s, on)["artifacts"]}
            repo_run = _run(pp, target, on, measure)
            result["repo"] = {"path": str(repo), "found": repo_run["found"],
                              "changes": _changes(repo_run["before"], repo_run["after"]),
                              "counts": repo_run["counts"], "unchanged": repo_run["unchanged"]}
    result["verdict"] = "CHANGES" if result["law"]["changes"] or (result["repo"] or {}).get("changes") else "NO_CHANGE"
    return result


def default_on() -> str:
    return dt.date.today().isoformat()
