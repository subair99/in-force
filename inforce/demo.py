"""Helpers for `inforce demo`: a throwaway copy of the demo repo, and a replay of the
recorded agent fix (demo/transcripts/agent-session.jsonl) so the demo needs no LLM,
no API key and no network."""
from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .paths import ROOT

DEMO_REPO = ROOT / "demo" / "naira-payroll"
AGENT_LOG = ROOT / "demo" / "transcripts" / "agent-session.jsonl"
LIVE_MARKER = "/demo/_live/"  # the recorded session edited demo/_live, a copy of the demo repo


def copy_demo(dest_parent: Path | None = None) -> Path:
    """Copy the demo repo (with its committed project graph) to a temp folder; return the copy."""
    parent = Path(dest_parent or tempfile.mkdtemp(prefix="inforce-demo-"))
    dst = parent / "naira-payroll"
    shutil.copytree(DEMO_REPO, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return dst


@dataclass
class Replay:
    edits: int = 0
    files: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def replay_agent_fix(repo: Path, log_path: Path = AGENT_LOG) -> Replay:
    """Apply the Write/Edit calls from the recorded session to `repo`, in order.

    Only edits inside the session's demo copy are replayed. An Edit whose old text is not
    found is reported, not forced.
    """
    out = Replay()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("type") != "assistant":
            continue
        for b in ev.get("message", {}).get("content", []):
            if b.get("type") != "tool_use" or b.get("name") not in ("Write", "Edit"):
                continue
            src = b["input"].get("file_path", "")
            if LIVE_MARKER not in src:
                continue
            rel = src.split(LIVE_MARKER, 1)[1]
            target = repo / rel
            if b["name"] == "Write":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(b["input"]["content"], encoding="utf-8")
            else:
                text = target.read_text(encoding="utf-8")
                old, new = b["input"]["old_string"], b["input"]["new_string"]
                if old not in text:
                    out.skipped.append(rel)
                    continue
                text = text.replace(old, new) if b["input"].get("replace_all") else text.replace(old, new, 1)
                target.write_text(text, encoding="utf-8")
            out.edits += 1
            if rel not in out.files:
                out.files.append(rel)
    return out
