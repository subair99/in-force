"""`inforce brief`: one screen on a file or a question, always in the same order.

VERDICT -> TRUTH -> WHY -> WHAT RESTS ON IT -> RE-CHECK LIST

For a file inside a repo, the repo is rescanned first (so the project graph is
current) and the brief is that file's slice of the scan. Anything else (a file
outside a repo, a question or a draft answer) is briefed from `check`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .check import DISCLAIMER, check_text
from .scan import scan

SECTIONS = ("verdict", "truth", "why", "rests_on_it", "recheck")


def find_repo_root(path: Path) -> Path | None:
    """Nearest ancestor with a project graph (.inforce/) or, failing that, a .git folder."""
    for marker in (".inforce", ".git"):
        for d in [path.parent, *path.parent.parents]:
            if (d / marker).is_dir():
                return d
    return None


def brief(target: str, on: str, law_pack: str | Path, repo: str | Path | None = None, log=None) -> dict[str, Any]:
    p = Path(target)
    if p.is_file():
        root = Path(repo).resolve() if repo else find_repo_root(p.resolve())
        if root is not None:
            out = brief_file(p.resolve(), root, on, law_pack, log)
            if out is not None:
                return out
        return brief_text(p.read_text(encoding="utf-8", errors="replace"), on, law_pack,
                          label=str(target), log=log)
    return brief_text(target, on, law_pack, label="text", log=log)


def _short(aid: str) -> str:
    return aid.split("::")[-1] if "::" in aid else aid


def _where(a: dict[str, Any]) -> str:
    return f"{a['path'] or a['id']}:{a['line']}" if a.get("line") and a.get("path") else (a.get("path") or a["id"])


def _truth_rows(becauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen, rows = set(), []
    for b in becauses:
        if b["target"] in seen:
            continue
        seen.add(b["target"])
        rows.append({"was": b.get("rule") or b["target"], "ref": b["target"], "endedOn": b.get("endedOn"),
                     "now": b.get("successor"), "nowRef": b.get("successorRef")})
    return rows


def brief_file(path: Path, root: Path, on: str, law_pack: str | Path, log=None) -> dict[str, Any] | None:
    rel = path.relative_to(root).as_posix()
    report = scan(root, on, law_pack, log=log)
    arts = {a["id"]: a for a in report["artifacts"]}
    mine = [a for a in report["artifacts"] if a["path"] == rel]
    if not mine:
        return None  # not a file scan looks at: fall back to checking its text

    order = {"STALE": 0, "SUSPECT": 1, "CURRENT": 2}
    verdict = min((a["status"] for a in mine), key=order.__getitem__)
    mine.sort(key=lambda a: (a.get("line") or 0, a["id"]))
    direct = [a for a in mine if a["status"] == "STALE" and not a["via"]]
    inherited = [a for a in mine if a["status"] == "STALE" and a["via"]]
    upstream = sorted({v for a in inherited for v in a["via"]} - {a["id"] for a in mine},
                      key=lambda u: (arts[u]["path"] or "", arts[u]["line"] or 0, u))

    becauses = [b for a in direct for b in a["because"]] + \
               [b for u in upstream for b in arts[u]["because"]]
    why = [{"artifact": a["id"], "line": b["line"], "claim": b.get("text"), "path": b["path"]}
           for a in direct for b in a["because"]]
    why += [{"artifact": a["id"], "chain": a["chain"]} for a in inherited]

    mine_ids = {a["id"] for a in mine}
    rests = sorted({r for a in mine for r in a["alsoCheck"]} - mine_ids)
    rests_on_it = [{"artifact": r, "kind": arts[r]["kind"], "where": _where(arts[r])} for r in rests if r in arts]

    recheck: list[dict[str, Any]] = []
    for u in upstream:  # fix the source first: this file is stale because of it
        a = arts[u]
        recheck.append({"where": _where(a), "artifact": u, "action": "fix first (this file depends on it)",
                        "replace": [{"was": b.get("rule"), "now": b.get("successor"), "nowRef": b.get("successorRef")}
                                    for b in a["because"]]})
    for a in direct:
        recheck.append({"where": _where(a) if a.get("line") else a["path"], "artifact": a["id"], "action": "update",
                        "replace": [{"line": b["line"], "was": b.get("rule"), "now": b.get("successor"),
                                     "nowRef": b.get("successorRef")} for b in a["because"]]})
    for a in inherited:
        recheck.append({"where": _where(a), "artifact": a["id"],
                        "action": "re-check after the fix (uses or tests it)"})
    for r in rests_on_it:
        recheck.append({"where": r["where"], "artifact": r["artifact"],
                        "action": f"re-check ({r['kind']} that rests on this file)"})

    return {
        "target": rel, "repo": str(root), "on": on, "verdict": verdict,
        "truth": _truth_rows(becauses), "why": why, "rests_on_it": rests_on_it, "recheck": recheck,
        "unverified": True if becauses else any(a["status"] == "SUSPECT" for a in mine),
        "path": [" ".join(b["path"]) for b in becauses if b.get("path")],
        "items": [{"artifact": a["id"], "status": a["status"]} for a in mine],
        "store": report["store"], "disclaimer": DISCLAIMER,
    }


def brief_text(text: str, on: str, law_pack: str | Path, label: str = "text", log=None) -> dict[str, Any]:
    r = check_text(text, on, law_pack, log=log)
    stale = [i for i in r["items"] if i["verdict"] == "REPEALED"]
    truth = [{"was": i["claim"], "ref": i["ref"], "endedOn": i["endedOn"], "now": i["successor"],
              "nowRef": i["successorRef"]} for i in stale]
    truth += [{"was": None, "ref": i["ref"], "endedOn": None, "now": i["claim"], "nowRef": i["ref"],
               "status": i["verdict"]} for i in r["items"] if i["verdict"] in ("IN_FORCE", "SAVED")]
    return {
        "target": label, "repo": None, "on": on, "verdict": r["verdict"],
        "truth": truth,
        "why": [{"claim": i["claim"], "line": i["line"], "path": i["path"], "note": i["note"]} for i in r["items"]],
        "rests_on_it": [],
        "recheck": [{"where": f"line {i['line']}", "artifact": i["claim"], "action": "rewrite",
                     "replace": [{"was": i["claim"], "now": i["successor"], "nowRef": i["successorRef"]}]}
                    for i in stale]
                   + [{"where": f"line {i['line']}", "artifact": i["claim"], "action": "could not check; say so",
                       "replace": []} for i in r["items"] if i["verdict"] == "NOT_RECOGNISED"],
        "unverified": r["unverified"], "path": r["path"], "items": r["items"], "disclaimer": DISCLAIMER,
    }
