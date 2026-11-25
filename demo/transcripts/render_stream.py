"""Render a `claude -p --output-format stream-json --verbose` log.

  ... | python render_stream.py              # live, readable terminal view (used in the recording)
  python render_stream.py --markdown LOG.jsonl > agent-session.md
"""
from __future__ import annotations

import json
import sys

DIM, BOLD, RED, GREEN, CYAN, YELLOW, RESET = "\033[2m", "\033[1m", "\033[31m", "\033[32m", "\033[36m", "\033[33m", "\033[0m"


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content)


def unwrap(raw: str):
    """MCP tool results arrive as {"result": "<json text>"}: return the inner object if there is one."""
    try:
        env = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(env, dict) and set(env) == {"result"} and isinstance(env["result"], str):
        try:
            return json.loads(env["result"])
        except ValueError:
            return env
    return env


def summarise_result(raw: str) -> str:
    """One line for an InForce JSON envelope; first lines of anything else."""
    env = unwrap(raw)
    if env is None:
        lines = raw.strip().splitlines()
        return "\n".join(lines[:6]) + (f"\n... ({len(lines) - 6} more lines)" if len(lines) > 6 else "")
    if not isinstance(env, dict) or "verdict" not in env:
        return raw[:400]
    parts = [f"verdict={env['verdict']}"]
    if "artifacts" in env:
        st = [a["status"] for a in env["artifacts"]]
        parts.append(f"STALE={st.count('STALE')} SUSPECT={st.count('SUSPECT')} CURRENT={st.count('CURRENT')}")
    if "recheck" in env:
        parts.append(f"recheck={len(env['recheck'])} items")
    if "items" in env and "artifacts" not in env and "recheck" not in env:
        parts.append(f"claims={len(env['items'])}")
    return " ".join(parts)


def events(stream):
    for line in stream:
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def tool_label(block: dict) -> str:
    name = block.get("name", "?")
    args = json.dumps(block.get("input", {}), ensure_ascii=False)
    return f"{name}({args[:300]}{'...' if len(args) > 300 else ''})"


def live(stream) -> None:
    names = {}
    for ev in events(stream):
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            tools = [x for x in ev.get("tools", []) if x.startswith("mcp__")]
            print(f"{DIM}session {ev.get('session_id', '')[:8]}  model={ev.get('model')}  mcp tools: {', '.join(tools)}{RESET}")
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    print(f"\n{BOLD}claude:{RESET} {b['text'].strip()}")
                elif b.get("type") == "tool_use":
                    names[b.get("id")] = b.get("name")
                    print(f"\n{CYAN}▶ {tool_label(b)}{RESET}")
        elif t == "user":
            content = ev.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    s = summarise_result(_text(b.get("content")))
                    colour = RED if "STALE=" in s and "STALE=0" not in s or "verdict=STALE" in s else GREEN
                    if b.get("is_error"):
                        colour = YELLOW
                    print(f"{colour}◀ {names.get(b.get('tool_use_id'), 'result')}: {s}{RESET}")
        elif t == "result":
            print(f"\n{DIM}done: {ev.get('subtype')}  turns={ev.get('num_turns')}  "
                  f"duration={ev.get('duration_ms', 0) / 1000:.0f}s  cost=${ev.get('total_cost_usd', 0):.2f}{RESET}")
        sys.stdout.flush()


def markdown(stream) -> str:
    out, names, n = [], {}, 0
    for ev in events(stream):
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            out.append(f"- Session model: `{ev.get('model')}`; Claude Code {ev.get('claude_code_version', '')}")
            out.append(f"- MCP tools available: {', '.join('`'+x+'`' for x in ev.get('tools', []) if x.startswith('mcp__'))}\n")
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text" and b.get("text", "").strip():
                    out.append(f"**Claude:** {b['text'].strip()}\n")
                elif b.get("type") == "tool_use":
                    n += 1
                    names[b.get("id")] = b.get("name")
                    out.append(f"### {n}. `{b.get('name')}`\n\n```json\n{json.dumps(b.get('input', {}), indent=2, ensure_ascii=False)}\n```\n")
        elif t == "user":
            content = ev.get("message", {}).get("content", [])
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "tool_result":
                    raw = _text(b.get("content"))
                    if not raw.strip():
                        continue  # e.g. ToolSearch loading tool schemas
                    flag = " (error)" if b.get("is_error") else ""
                    out.append(f"Result{flag}: **{summarise_result(raw).splitlines()[0]}**\n")
                    inner = unwrap(raw)
                    body = json.dumps(inner, indent=2, ensure_ascii=False) if isinstance(inner, dict) else raw
                    lang = "json" if isinstance(inner, dict) else ""
                    if len(body) > 6000:
                        body = body[:6000] + "\n... (truncated; full text in the .jsonl)"
                    out.append(f"<details><summary>full result</summary>\n\n```{lang}\n{body}\n```\n</details>\n")
        elif t == "result":
            out.append(f"---\n\nFinished: `{ev.get('subtype')}`, {ev.get('num_turns')} turns, "
                       f"{ev.get('duration_ms', 0) / 1000:.0f}s, ${ev.get('total_cost_usd', 0):.2f}.\n")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--markdown":
        with open(sys.argv[2], encoding="utf-8") as f:
            print(markdown(f))
    else:
        live(sys.stdin)
