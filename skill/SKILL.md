---
name: inforce
description: Check Nigerian tax law citations and tax-computing code against law in force before answering or editing. Use for questions on PAYE, personal or company income tax, CGT, VAT or tax incentives in Nigeria, and before editing payroll or tax code.
---

# InForce

Nigeria repealed its main tax Acts on 1 January 2026. Your training data may still reflect the old law.

Before you:
- **answer** a question that cites or relies on Nigerian tax law → call `inforce_check` with your draft answer. Replace every claim marked REPEALED with the successor rule it returns, and cite the new provision.
- **edit** a file that computes tax, payroll or invoices → call `inforce_brief` with the file path. Follow the re-check list; update the code, its tests and any documents listed under "also check".
- **finish** such an edit → call `inforce_scan` on the repo and confirm zero STALE artifacts.

Rules:
- Treat a SAVED status as still applicable, for the period stated.
- If a rule is marked unverified, say so in your answer.
- Never state tax figures that InForce did not return. Say what you could not check.
- Add: "This is not legal or tax advice."

Raw Cypher, read-only, is also available: `relate serve --mcp stdio --database data/ng-tax-2026.rl --read-only`.
