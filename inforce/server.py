"""MCP server (stdio): `inforce serve`. Built with Relate.

Three tools, each opening the store(s) for one call and closing them again,
so an agent and `inforce scan` can share a project graph (a locked store is
retried, then reported). Every verdict comes from Cypher against Relate.
Uses the MCP Python SDK 2.x (`MCPServer`, formerly FastMCP).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from .brief import brief
from .check import check_text
from .paths import LAW_PACK
from .scan import record_answer, scan
from .store import StoreLocked

INSTRUCTIONS = (
    "InForce checks Nigerian tax law claims and tax code against the law in force on a date "
    "(Nigeria Tax Act 2025 replaced PITA, CITA, CGTA, VAT Act and others on 1 Jan 2026). "
    "Call inforce_check on a draft answer before sending it; replace every REPEALED claim with the "
    "successor it returns. Call inforce_brief on a tax/payroll file before editing it and follow the "
    "re-check list. Call inforce_scan on the repo after editing; aim for zero STALE. "
    "Rules marked unverified must be reported as unverified. Not legal or tax advice."
)


def _on(on: str | None) -> str:
    return dt.date.fromisoformat(on).isoformat() if on else dt.date.today().isoformat()


def _json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _log(msg: str) -> None:
    print(f"inforce: {msg}", file=sys.stderr, flush=True)  # stdout is the MCP channel


def _guard(fn, *args) -> str:
    try:
        return _json(fn(*args))
    except StoreLocked as exc:
        return _json({"verdict": "ERROR", "error": "store_locked", "message": str(exc), "retryable": True})


def build_server(law_pack: str | Path = LAW_PACK) -> MCPServer:
    law_pack = Path(law_pack).resolve()
    mcp = MCPServer(name="inforce", instructions=INSTRUCTIONS)

    @mcp.tool(description=(
        "Check a text (draft answer, document) for Nigerian tax law citations and figures. "
        "Returns JSON {verdict: STALE|SUSPECT|CURRENT|NO_CLAIMS, items[], path[], on, disclaimer}. "
        "Each item has verdict, endedOn, successor (what replaced it) and a proof path. "
        "Pass record_in=<repo path> to also store the answer in that repo's project graph."))
    def inforce_check(text: str, on: str | None = None, record_in: str | None = None,
                      answer_id: str | None = None) -> str:
        def run():
            d = _on(on)
            result = check_text(text, d, law_pack, log=_log)
            if record_in:
                import hashlib
                aid = answer_id or hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
                rec = record_answer(record_in, aid, text, d, law_pack, log=_log)
                result["recorded"] = {"artifact": rec["artifact"]["id"], "status": rec["verdict"]}
            return result
        return _guard(run)

    @mcp.tool(description=(
        "Scan a repo or folder: which code constants, functions, tests, documents and templates rest on "
        "repealed Nigerian tax law, and what uses or tests them. Writes <path>/.inforce/project.rl. "
        "Returns JSON {verdict, artifacts[{id, status, because[], via[], chain[], alsoCheck[]}], on}."))
    def inforce_scan(path: str, on: str | None = None) -> str:
        return _guard(lambda: scan(path, _on(on), law_pack, log=_log))

    @mcp.tool(description=(
        "Brief on one file (rescans its repo) or on a question / draft answer, in fixed order: "
        "verdict, truth (what the law says now), why (graph proof), rests_on_it, recheck (ordered list "
        "of what to change, with old -> new rule). Call before editing tax or payroll code."))
    def inforce_brief(target: str, on: str | None = None, repo: str | None = None) -> str:
        return _guard(lambda: brief(target, _on(on), law_pack, repo=repo, log=_log))

    return mcp


def main() -> None:
    build_server().run("stdio")


if __name__ == "__main__":
    main()
