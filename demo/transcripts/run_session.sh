#!/usr/bin/env bash
# The recorded agent session: headless Claude Code fixing a throwaway copy of the demo repo
# through the InForce MCP tools. Run from the repo root on a fresh copy:
#   cp -r demo/naira-payroll demo/_live
#   asciinema rec demo/transcripts/agent-session.cast --overwrite --cols 120 --rows 40 -c "bash demo/transcripts/run_session.sh"
set -o pipefail
PROMPT="Use the inforce MCP tools. First call inforce_brief on demo/_live/payroll/paye.py and summarise the verdict. Then fix paye.py and its test so they follow the successor rules InForce returns, and update any other files it lists under 'also check'. After each change, run inforce_scan on demo/_live until it reports zero STALE artifacts. Do not touch demo/naira-payroll, do not commit, and cite the provisions InForce returns. Zero STALE means every file the scan flags in demo/_live, including payroll/company_tax.py and its test, docs/hr-policy.md and templates/payslip.html; rewrite answers/stale_answer.md to current law rather than deleting it."
echo "\$ claude -p \"$PROMPT\""
echo
claude -p "$PROMPT" \
  --mcp-config .mcp.json --strict-mcp-config \
  --allowedTools 'mcp__inforce__*,mcp__relate-law__*,Read,Edit,Write,Bash(inforce:*)' \
  --permission-mode dontAsk \
  --output-format stream-json --verbose \
  | tee demo/transcripts/agent-session.jsonl \
  | python demo/transcripts/render_stream.py
