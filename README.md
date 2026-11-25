# InForce

**Find every AI answer, line of code and document that still runs on repealed law, and see what replaced it.** Built with Relate.

> On 1 January 2026 Nigeria's new Tax Act came into force and repealed the country's main tax laws. Payroll code, HR policies and AI assistants written before then still use the old rules. InForce finds them.

*InForce checks whether a provision is in force. It is not legal or tax advice.*

<!-- TODO: GIF of `inforce scan` turning the demo repo red, then green -->

## First result in 60 seconds

```bash
git clone [REPO_URL] && cd inforce
make install        # Windows without make: python -m pip install -e ".[dev,embed]"
make demo           # Windows without make: inforce load --allow-unverified; inforce demo --fast
```

Expected output: <!-- TODO: paste real output -->

## Use case

[TODO: 3–4 sentences. Who: developers of Nigerian payroll, accounting and tax-assistant software, plus accountants who paste AI answers into the checker. Problem: repealed rules hide in code, tests, policies and AI answers. Relationships that matter: `REPEALS`, `SAVES`, `SUCCEEDED_BY`, `REPLACED_BY`, `ENCODES`, `CITES`, `TESTED_BY`/`USED_BY`.]

## How it uses Relate

- **Mode:** single file, twice.
  - `data/ng-tax-2026.rl`: the law pack (Acts, provisions, rules, repeals, savings, successors), read-only at runtime.
  - `<your repo>/.inforce/project.rl`: the project graph (files, constants, tests, documents and the rules they encode), committed with the code.
- **Why this mode:** [TODO: one file judges can inspect; the law travels as one shippable dataset; the project graph is committed like a lockfile so a PR shows the re-check list changing; no server. Explain why we open and close per command (a `.rl` file is locked while a writer holds it).]
- **What the graph models:** [TODO: node and relationship tables from docs/SPEC.md §3, and the rule: a provision is in force on a date unless repealed with no saving; artifacts inherit status from the rules they encode.]
- **Relate features used:** embedded Python (`relate-db`), Cypher with variable-length paths, transactions with rollback (`whatif`), serialized writers, vector + full-text `SEARCH`, MCP (`relate serve --mcp stdio`), agent skill. [TODO: browser build if shipped]

## Setup and run

Prerequisites: Python 3.11+, the Relate CLI ([install](https://relatedb.ai/docs/get-started/install/)).

[TODO: install steps for macOS/Linux and Windows, then each command with an example:]

```bash
inforce check demo/naira-payroll/answers/stale_answer.md
inforce scan demo/naira-payroll
inforce brief demo/naira-payroll/payroll/paye.py
inforce whatif repeal [AKN]
inforce keystones
```

### Use it from your coding agent (Claude Code)

From the repo root, with the virtualenv active so `inforce` is on your `PATH`:

```bash
cp .mcp.json.example .mcp.json                      # two MCP servers: inforce + Relate's own (read-only law pack)
mkdir -p .claude/skills/inforce && cp skill/SKILL.md .claude/skills/inforce/
claude                                              # approve the two project MCP servers when asked
claude mcp list                                     # inforce and relate-law should show as connected
```

| MCP server | Tools | What it gives the agent |
|---|---|---|
| `inforce` (`inforce serve`) | `inforce_check`, `inforce_brief`, `inforce_scan` | verdicts, successor rules, proof paths and re-check lists (JSON) |
| `relate-law` (`relate serve --mcp stdio --read-only --safe`) | `read_cypher`, `get_schema` | raw read-only Cypher on the law pack |

The skill tells the agent to check a draft answer before sending it, to brief a tax file before editing it, and to rescan until nothing is STALE. Pass `record_in` to `inforce_check` (or `--record <repo>` on the CLI) and the answer is stored in that repo's project graph next to the code, so a later scan also flags AI answers that rest on repealed law.

Two writers, one store: `python scripts/two_writers.py` holds the project graph open (a simulated long scan) while an agent records an answer. The agent's `store locked, retry n/3` lines show it waiting its turn, then both writes land.

## Where the data lives

- Law pack: `data/ng-tax-2026.rl` (built from `data/rules/*.yaml`, each rule with its source link)
- Demo project graph: `demo/naira-payroll/.inforce/project.rl`

Inspect them yourself:

```bash
relate --database data/ng-tax-2026.rl --read-only --mode envelope "MATCH (i:Instrument)-[:REPEALS]->(old) RETURN i.title, old.title LIMIT 20"
relate --database demo/naira-payroll/.inforce/project.rl --read-only --mode envelope "MATCH (a:Artifact)-[:ENCODES]->(r:Rule) RETURN a.id, r.text LIMIT 20"
```

## Data and accuracy

Hand-built from the official Acts: identifiers, dates, relationships, rule values and short summaries in our own words, each linked to its source. `make verify` lists every rule and whether it has been checked against the Act's text. [TODO: state how many rules are verified at submission.] The demo payroll repo is synthetic.

## Built with

Relate by Neo4j, Python, Typer, Rich, PyYAML, MCP Python SDK, model2vec. AI tools: [TODO: list each tool and what it did]. Reused work: [TODO: none / list].

## Limits and what's next

[TODO: honest limits (scan patterns are explicit, not exhaustive; Nigerian federal tax only). Next: law packs for other countries via Akoma Ntoso; state tax laws; a GitHub Action that comments the re-check list on PRs.]

## License

MIT
