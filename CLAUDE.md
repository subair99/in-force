# CLAUDE.md — InForce

You are building **InForce** for the Relate by Neo4j Hackathon (Devpost). Read this file first, then `docs/SPEC.md`, `docs/PLAN.md` and `docs/HACKATHON_RULES.md`.

## One-line pitch
InForce finds every AI answer, line of code and document that still runs on repealed law, and shows what replaced it. Demo domain: Nigeria's tax overhaul (Nigeria Tax Act 2025, in force 1 January 2026).

## Hard deadline
Devpost closes **11 Dec 2026, 6:00 PM PST** (12 Dec, 3:00 AM Lagos). Target submission: **10 Dec**. Feature freeze: **8 Dec**.

## Non-negotiable rules (from the hackathon)
1. This repo must be **public**, created on or after 11 Nov 2026, with GitHub topics `relate` (required) and `relate-neo4j-hackathon`.
2. Relate must actually run. Every verdict comes from a Cypher query against Relate. No prompt-only features.
3. Persistent stores are committed: `data/ng-tax-2026.rl` and `demo/naira-payroll/.inforce/project.rl`.
4. `make demo` must work on a fresh clone with **no API keys and no network** beyond package install.
5. Synthetic demo data only. No real people, salaries or client material.
6. Never imply Neo4j endorses the project. Say "Built with Relate".

## How to work in this repo
- **Verify before you build.** Relate is new (v1.3.0, released 25 Nov 2026; CLI and `relate-db` both pinned to 1.3.0) and your training data may not know it. Run `scripts/spike_relate.py` first and fix this file's assumptions from what it prints. Use `relate agent-context`, the installed skill (`~/.claude/skills/relate/`, docs offline) and https://relatedb.ai/docs/llms.txt for the real API. Spike results: `docs/SPIKE_RESULTS.md`. Do not guess method names.
- **Never invent law.** Every `Rule` in `data/rules/*.yaml` starts as `verified: false`. Do not change a value or set `verified: true` yourself. The human checks each one against the Act's text. The loader refuses any law entry (instrument, provision, rule, repeal, replacement, grant, saving) whose `verified` is not `true` (a missing flag counts as false) unless `--allow-unverified` is passed. It never rewrites a value: a `TODO` date is left unset with a warning. The demo uses that flag until verification is done, and the README says so.
- **Store summaries, not law text.** Keep identifiers, dates, relationships, numbers and short summaries in our own words, with a source URL. Never paste whole sections of an Act.
- **Open and close the store per command.** A `.rl` file cannot be opened, even read-only, while a writer holds it. No long-lived connections, no thread pools (a Python connection is bound to the thread that opened it, `close()` included). Retry on exit code 5 / lock errors up to 3 times with backoff. From Python a lock is `relate.OperationalError("storage locked: …")` with `retryable=False`; always go through `inforce.store.open_store`, which handles it and raises `StoreLocked` (exit 5).
- **Every read query has a `LIMIT`**, aggregates included. The CLI's `--safe` mode rejects `MATCH … RETURN/WITH` without one; the Python client has no safe mode, so `Store.execute` enforces it (`check_bounded`) and `tests/test_queries.py` runs every read query through `relate --safe`.
- **One statement per `execute()`.** A `;`-joined string is a syntax error. `BEGIN`/`ROLLBACK` as Cypher text is also a syntax error from Python: use `Store.transaction()` / `Store.rollback_only()` (they set `autocommit = False`, then `commit()`/`rollback()`).
- **CLI `--param` values are JSON.** Quote dates: `--param on='"2026-03-01"'` (a bare `2026-03-01` is a malformed number).
- **One statement reads one graph.** Cross-store work (law pack + project graph) happens by copying the referenced `Rule`/`Provision` nodes into the project graph during `scan`.
- **Queries live in `inforce/queries/*.cypher`**, one per file, loaded by name. No Cypher strings scattered in Python.
- **Keep it boring:** Python 3.11, Typer + Rich for the CLI, PyYAML, pytest. Pin `relate-db` exactly. Optional: `model2vec` for local embeddings. No web framework; the browser page is static HTML.
- **Tests first for the truth rules:** in force on a date, repeal, saving clause, successor chain, artifact inheritance, what-if rollback leaves the store unchanged.
- **Commit small, commit often** with clear messages. Tick tasks in `docs/PLAN.md` as you finish them.
- **Git: of the planning documents, only this CLAUDE.md is tracked.** Everything under `docs/` (SPEC, PLAN, HACKATHON_RULES, KICKOFF_PROMPT, DEVPOST, SPIKE_RESULTS) is private and listed in `.gitignore`. Read and update those files locally, but never `git add` them, never use `git add -f`, and never remove `docs/` from `.gitignore`. Stage files by name, or run `git status` before `git add -A`, and check that no `docs/` path is staged. Product files (code, README, data, `.rl` stores, skill, tests) are committed as normal; judges need them.

## Priorities
P0: `check`, `scan`, `brief`, MCP server + skill, `make demo`, README.
P1: `whatif`, `keystones`, `ask --on`, `diff --known-on`.
P2: browser checker (static first, WebAssembly + OPFS only if time allows).
If time is short, cut from the bottom. Never cut tests, the README or reproducibility.

## Disclaimer (show in CLI output footer, README and browser page)
"InForce checks whether a provision is in force. It is not legal or tax advice."
