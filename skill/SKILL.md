---
name: inforce
description: Check Nigerian tax law citations and tax-computing code against the law in force before answering or editing. Use for questions on PAYE, personal or company income tax, CGT, VAT or tax incentives in Nigeria, and before editing payroll or tax code.
---

# InForce

Nigeria's main tax Acts (PITA, CITA, CGTA, VAT Act, IDITRA and others) were repealed on 1 January 2026 by the Nigeria Tax Act 2025. Your training data may still reflect the old law. InForce answers from a graph of the law (Relate), not from memory.

## Tools (MCP server `inforce`, started with `inforce serve`)

| Tool | Arguments | Use it to |
|---|---|---|
| `inforce_check` | `text`, `on?` (YYYY-MM-DD), `record_in?` (repo path), `answer_id?` | check a draft answer or document. `record_in` also stores the answer in that repo's project graph |
| `inforce_brief` | `target` (file path or question), `on?`, `repo?` | get one screen on a file before editing it: verdict, truth, why, what rests on it, re-check list |
| `inforce_scan` | `path`, `on?` | list every artifact in a repo resting on repealed law, and what uses or tests it |

All return JSON. A verdict of `STALE` means something rests on repealed law. Each item carries `successor` / `now`, the rule that replaced it, and a `path`, the graph proof.

## Before you answer a question that relies on Nigerian tax law
1. Draft the answer, then call `inforce_check` with it.
2. Replace every claim marked `REPEALED` with the `successor` it returns, and cite the new Act.
3. Claims marked `NOT_RECOGNISED` could not be checked: say so, do not guess figures.
4. If the user is working in a repo, pass `record_in` so the answer is tracked with the code.

## Before you edit a file that computes tax, payroll or invoices
1. Call `inforce_brief` with the file path.
2. Work through `recheck` in order. Items marked "fix first" are upstream: change them before the file itself.
3. Update the code, its tests and every document or template listed. Use the `now` rule for each change.
4. Call `inforce_scan` on the repo and confirm zero `STALE` artifacts before you finish.

## Rules
- Treat `SAVED` as still applicable, for the period stated.
- Every rule in the current law pack is marked unverified (not yet checked against the Act's text by a human). Say so when you rely on one.
- Never state a tax figure that InForce did not return.
- End with: "This is not legal or tax advice."

Raw, read-only Cypher on the law pack is also available through Relate's own MCP server (tools `read_cypher`, `get_schema`):
`relate serve --mcp stdio --database data/ng-tax-2026.rl --read-only --safe`
