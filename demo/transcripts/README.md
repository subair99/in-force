# Recorded agent sessions

Two headless Claude Code sessions use the InForce MCP server on a throwaway copy of the
synthetic demo repo (`demo/_live`, a copy of `demo/naira-payroll`, deleted afterwards and never committed).

| Session | What it shows |
|---|---|
| [agent-refusal.md](agent-refusal.md) | First run, when the law pack lacked the middle 2026 PAYE bands. The agent **refuses to invent the missing law**: it stops before editing and says what is missing. |
| [agent-session.md](agent-session.md) | Run after the bands and the scale succession were added. The agent briefs `paye.py`, fixes code, tests, policy, template and answer, and rescans until **zero STALE**. |

Each session has `.cast` (asciinema), `.gif` and `.mp4` (rendered) and `.jsonl` (raw `stream-json` events) files.

## How they were produced

```bash
cp -r demo/naira-payroll demo/_live                  # throwaway copy, excluded via .git/info/exclude
cp .mcp.json.example .mcp.json                       # servers: inforce, relate-law
asciinema rec demo/transcripts/agent-session.cast --overwrite --cols 120 --rows 40 -i 3 \
  -c "bash demo/transcripts/run_session.sh"
agg --idle-time-limit 3 --font-size 14 demo/transcripts/agent-session.cast demo/transcripts/agent-session.gif
ffmpeg -i demo/transcripts/agent-session.gif -movflags +faststart -pix_fmt yuv420p \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" demo/transcripts/agent-session.mp4
python demo/transcripts/render_stream.py --markdown demo/transcripts/agent-session.jsonl   # transcript body
rm -rf demo/_live
```

- **`run_session.sh`** runs `claude -p` with:
  - `--mcp-config .mcp.json --strict-mcp-config`: only the repo's two MCP servers.
  - `--allowedTools 'mcp__inforce__*,mcp__relate-law__*,Read,Edit,Write,Bash(inforce:*)'`
  - `--permission-mode dontAsk`: anything else is refused, not prompted.
  - `--output-format stream-json --verbose`: every tool call and result.

  The JSON stream is saved with `tee` and shown live through `render_stream.py`, which is what the recording shows.
- **Versions:** Claude Code 2.1.332, Relate 1.3.0, asciinema 2.4.0, agg 1.9.0.
- **Not deterministic:** a re-run gives a different session.
- **Before publishing**, the `.jsonl` init events were trimmed of local environment details (installed plugins and skills, memory paths, session ids).
- **Synthetic data:** no real people or salaries. Law values are unverified. Not legal or tax advice.
