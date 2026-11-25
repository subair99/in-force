# Agent refusal: Claude Code will not invent missing law

The first recording, 25 November 2026, made with the same setup as [agent-session.md](agent-session.md).
At that point the law pack held only three of the 2026 PAYE bands. The agent was asked to fix `paye.py`
using the successor rules InForce returns. It called `inforce_brief` and `inforce_scan`, then ran
`inforce_check` on the middle bands it remembered. Those came back NOT_RECOGNISED. **It then
stopped without editing anything**, because writing them from memory would have meant inventing law.
It explained the gap and offered options.

The missing bands were then added to `data/rules/ng-tax-2026.yaml` (still unverified), and the
whole PIT scale was linked as replaced by NTA s. 58 (`successions:`). The second run,
[agent-session.md](agent-session.md), then fixed the repo.

Recording: [agent-refusal.gif](agent-refusal.gif) / [agent-refusal.mp4](agent-refusal.mp4) / [agent-refusal.cast](agent-refusal.cast). Raw log: [agent-refusal.jsonl](agent-refusal.jsonl).
13 turns, $0.39. The prompt was the one in [agent-session.md](agent-session.md), without its last sentence. That sentence, on what zero STALE covers, was added for the second run after the agent asked about scope. This run's allow-list also lacked `mcp__relate-law__*`, so its raw Cypher query was refused.

## Transcript

- Session model: `claude-opus-5-5`; Claude Code 2.1.332
- MCP tools available: `mcp__inforce__inforce_brief`, `mcp__inforce__inforce_check`, `mcp__inforce__inforce_scan`, `mcp__relate-law__get_schema`, `mcp__relate-law__read_cypher`

### 1. `ToolSearch`

```json
{
  "query": "select:mcp__inforce__inforce_brief,mcp__inforce__inforce_scan,mcp__inforce__inforce_check"
}
```

### 2. `mcp__inforce__inforce_brief`

```json
{
  "target": "demo/_live/payroll/paye.py"
}
```

Result: **verdict=STALE recheck=7 items**

<details><summary>full result</summary>

```json
{
  "target": "payroll/paye.py",
  "repo": "/home/user/in-force/demo/_live",
  "on": "2026-11-25",
  "verdict": "STALE",
  "truth": [
    {
      "was": "PIT: next NGN 300,000 at 11%",
      "ref": "ng.pit.band2.old",
      "endedOn": "2026-01-01",
      "now": "PIT: next NGN 2,200,000 at 15%",
      "nowRef": "ng.pit.band2.2026"
    },
    {
      "was": "PIT: first NGN 300,000 at 7%",
      "ref": "ng.pit.band1.old",
      "endedOn": "2026-01-01",
      "now": "PIT: first NGN 800,000 at 0%",
      "nowRef": "ng.pit.band1.2026"
    },
    {
      "was": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
      "ref": "ng.pit.cra.old",
      "endedOn": "2026-01-01",
      "now": "Rent relief: 20% of annual rent, capped at NGN 500,000",
      "nowRef": "ng.pit.rent_relief.2026"
    }
  ],
  "why": [
    {
      "artifact": "payroll/paye.py::PIT_BANDS_2025",
      "line": 4,
      "claim": "PIT_BANDS_2025",
      "path": [
        "Rule ng.pit.band2.old",
        "<-SETS- Provision TODO/ng/act/pita/sec_bands",
        "<-CONTAINS- Instrument PITA",
        "<-REPEALS 2026-01-01- Instrument NTA"
      ]
    },
    {
      "artifact": "payroll/paye.py::PIT_BANDS_2025",
      "line": 4,
      "claim": "PIT_BANDS_2025",
      "path": [
        "Rule ng.pit.band1.old",
        "<-SETS- Provision TODO/ng/act/pita/sec_bands",
        "<-CONTAINS- Instrument PITA",
        "<-REPEALS 2026-01-01- Instrument NTA"
      ]
    },
    {
      "artifact": "payroll/paye.py::CRA_RATE",
      "line": 14,
      "claim": "CRA_RATE",
      "path": [
        "Rule ng.pit.cra.old",
        "<-SETS- Provision TODO/ng/act/pita/sec_cra",
        "<-CONTAINS- Instrument PITA",
        "<-REPEALS 2026-01-01- Instrument NTA"
      ]
    },
    {
      "artifact": "payroll/paye.py::CRA_FLAT_MIN",
      "line": 15,
      "claim": "CRA_FLAT_MIN",
      "path": [
        "Rule ng.pit.cra.old",
        "<-SETS- Provision TODO/ng/act/pita/sec_cra",
        "<-CONTAINS- Instrument PITA",
        "<-REPEALS 2026-01-01- Instrument NTA"
      ]
    },
    {
      "artifact": "payroll/paye.py::consolidated_relief",
      "chain": [
        {
          "source": "payroll/paye.py::CRA_RATE",
          "type": "USED_BY",
          "target": "payroll/paye.py::consolidated_relief"
        }
      ]
    },
    {
      "artifact": "payroll/paye.py::compute_paye",
      "chain": [
        {
          "source": "payroll/paye.py::PIT_BANDS_2025",
          "type": "USED_BY",
          "target": "payroll/paye.py::compute_paye"
        }
      ]
    }
  ],
  "rests_on_it": [
    {
      "artifact": "payroll/payslip.py::build_payslip",
      "kind": "code",
      "where": "payroll/payslip.py:6"
    },
    {
      "artifact": "tests/test_paye.py",
      "kind": "test",
      "where": "tests/test_paye.py:1"
    }
  ],
  "recheck": [
    {
      "where": "payroll/paye.py:4",
      "artifact": "payroll/paye.py::PIT_BANDS_2025",
      "action": "update",
      "replace": [
        {
          "line": 4,
          "was": "PIT: next NGN 300,000 at 11%",
          "now": "PIT: next NGN 2,200,000 at 15%",
          "nowRef": "ng.pit.band2.2026"
        },
        {
          "line": 4,
          "was": "PIT: first NGN 300,000 at 7%",
          "now": "PIT: first NGN 800,000 at 0%",
          "nowRef": "ng.pit.band1.2026"
        }
      ]
    },
    {
      "where": "payroll/paye.py:14",
      "artifact": "payroll/paye.py::CRA_RATE",
      "action": "update",
      "replace": [
        {
          "line": 14,
          "was": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "now": "Rent relief: 20% of annual rent, capped at NGN 500,000",
          "nowRef": "ng.pit.rent_relief.2026"
        }
      ]
    },
    {
      "where": "payroll/paye.py:15",
      "artifact": "payroll/paye.py::CRA_FLAT_MIN",
      "action": "update",
      "replace": [
        {
          "line": 15,
          "was": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "now": "Rent relief: 20% of annual rent, capped at NGN 500,000",
          "nowRef": "ng.pit.rent_relief.2026"
        }
      ]
    },
    {
      "where": "payroll/paye.py:18",
      "artifact": "payroll/paye.py::consolidated_relief",
      "action": "re-check after the fix (uses or tests it)"
    },
    {
      "where": "payroll/paye.py:23",
      "artifact": "payroll/paye.py::compute_paye",
      "action": "re-check after the fix (uses or tests it)"
    },
    {
      "where": "payroll/payslip.py:6",
      "artifact": "payroll/payslip.py::build_payslip",
      "action": "re-check (code that rests on this file)"
    },
    {
      "where": "tests/test_paye.py:1",
      "artifact": "tests/test_paye.py",
      "action": "re-check (test that rests on this file)"
    }
  ],
  "unverified": true,
  "path": [
    "Rule ng.pit.band2.old <-SETS- Provision TODO/ng/act/pita/sec_bands <-CONTAINS- Instrument PITA <-REPEALS 2026-01-01- Instrument NTA",
    "Rule ng.pit.band1.old <-SETS- Provision TODO/ng/act/pita/sec_bands <-CONTAINS- Instrument PITA <-REPEALS 2026-01-01- Instrument NTA",
    "Rule ng.pit.cra.old <-SETS- Provision TODO/ng/act/pita/sec_cra <-CONTAINS- Instrument PITA <-REPEALS 2026-01-01- Instrument NTA",
    "Rule ng.pit.cra.old <-SETS- Provision TODO/ng/act/pita/sec_cra <-CONTAINS- Instrument PITA <-REPEALS 2026-01-01- Instrument NTA"
  ],
  "items": [
    {
      "artifact": "payroll/paye.py::PIT_BANDS_2025",
      "status": "STALE"
    },
    {
      "artifact": "payroll/paye.py::CRA_RATE",
      "status": "STALE"
    },
    {
      "artifact": "payroll/paye.py::CRA_FLAT_MIN",
      "status": "STALE"
    },
    {
      "artifact": "payroll/paye.py::consolidated_relief",
      "status": "STALE"
    },
    {
      "artifact": "payroll/paye.py::compute_paye",
      "status": "STALE"
    }
  ],
  "store": "/home/user/in-force/demo/_live/.inforce/project.rl",
  "disclaimer": "InForce checks whether a provision is in fo
... (truncated; full text in the .jsonl)
```
</details>

### 3. `Bash`

```json
{
  "command": "find demo/_live -type f -not -path '*/.inforce/*' | head -50 && git status --short",
  "description": "List live demo files and git status"
}
```

Result: **demo/_live/README.md**

<details><summary>full result</summary>

```
demo/_live/README.md
demo/_live/payroll/__init__.py
demo/_live/payroll/paye.py
demo/_live/payroll/payslip.py
demo/_live/payroll/company_tax.py
demo/_live/templates/payslip.html
demo/_live/answers/stale_answer.md
demo/_live/docs/hr-policy.md
demo/_live/tests/test_paye.py
demo/_live/tests/test_company_tax.py
?? demo/transcripts/
```
</details>

### 4. `Bash`

```json
{
  "command": "cd /home/user/in-force/demo/_live && for f in payroll/paye.py payroll/payslip.py tests/test_paye.py README.md; do echo \"=== $f\"; cat -n $f; done; git -C /home/user/in-force check-ignore -v demo/_live; git -C /home/user/in-force ls-files demo/_live | head",
  "description": "Show paye, payslip, test and README files"
}
```

Result (error): **Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.**

<details><summary>full result</summary>

```
Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.
```
</details>

### 5. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/payroll/paye.py"
}
```

Result: **1	"""PAYE for monthly payroll. SYNTHETIC DEMO CODE, written as of 2025."""**

<details><summary>full result</summary>

```
1	"""PAYE for monthly payroll. SYNTHETIC DEMO CODE, written as of 2025."""
2	
3	# Annual taxable-income bands: (width of band in NGN, rate). Last band is open-ended.
4	PIT_BANDS_2025 = (
5	    (300_000, 0.07),
6	    (300_000, 0.11),
7	    (500_000, 0.15),
8	    (500_000, 0.19),
9	    (1_600_000, 0.21),
10	    (None, 0.24),
11	)
12	
13	# Consolidated relief: a share of gross income plus a fixed floor.
14	CRA_RATE = 0.20
15	CRA_FLAT_MIN = 200_000
16	
17	
18	def consolidated_relief(gross: float) -> float:
19	    """Relief deducted from annual gross income before the bands apply."""
20	    return CRA_RATE * gross + max(CRA_FLAT_MIN, 0.01 * gross)
21	
22	
23	def compute_paye(gross: float) -> float:
24	    """Annual PAYE on an annual gross income, in NGN."""
25	    taxable = max(0.0, gross - consolidated_relief(gross))
26	    tax = 0.0
27	    for width, rate in PIT_BANDS_2025:
28	        if width is None or taxable <= width:
29	            tax += taxable * rate
30	            break
31	        tax += width * rate
32	        taxable -= width
33	    return round(tax, 2)
34	
```
</details>

### 6. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/tests/test_paye.py"
}
```

Result: **1	"""Tests pinned to the 2025 results. SYNTHETIC DEMO."""**

<details><summary>full result</summary>

```
1	"""Tests pinned to the 2025 results. SYNTHETIC DEMO."""
2	
3	from payroll.paye import compute_paye
4	
5	
6	def test_below_relief_pays_nothing():
7	    assert compute_paye(200_000) == 0.0
8	
9	
10	def test_mid_income():
11	    # gross 3,000,000: relief 600,000 + 200,000 = 800,000; taxable 2,200,000
12	    # 300k@7% + 300k@11% + 500k@15% + 500k@19% + 600k@21% = 21k + 33k + 75k + 95k + 126k
13	    assert compute_paye(3_000_000) == 350_000.0
14	
```
</details>

### 7. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/payroll/payslip.py"
}
```

Result: **1	"""Monthly payslip figures. SYNTHETIC DEMO CODE."""**

<details><summary>full result</summary>

```
1	"""Monthly payslip figures. SYNTHETIC DEMO CODE."""
2	
3	from payroll.paye import compute_paye
4	
5	
6	def build_payslip(employee_id: str, annual_gross: float) -> dict:
7	    """Figures for one month's payslip. employee_id is a made-up identifier."""
8	    annual_tax = compute_paye(annual_gross)
9	    monthly_gross = annual_gross / 12
10	    monthly_tax = round(annual_tax / 12, 2)
11	    return {
12	        "employee": employee_id,
13	        "gross": round(monthly_gross, 2),
14	        "paye": monthly_tax,
15	        "net": round(monthly_gross - monthly_tax, 2),
16	    }
17	
```
</details>

### 8. `ToolSearch`

```json
{
  "query": "select:mcp__relate-law__read_cypher,mcp__relate-law__get_schema"
}
```

**Claude:** The brief says paye.py is **STALE**. I'm now checking the law pack for the full set of successor PIT bands before I edit anything.

### 9. `mcp__relate-law__read_cypher`

```json
{
  "statement": "MATCH (r:Rule) WHERE r.id STARTS WITH 'ng.pit' RETURN r LIMIT 50"
}
```

Result (error): **Permission to use mcp__relate-law__read_cypher has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.**

<details><summary>full result</summary>

```
Permission to use mcp__relate-law__read_cypher has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.
```
</details>

### 10. `Read`

```json
{
  "file_path": "/home/user/in-force/data/rules/pit.yaml"
}
```

Result (error): **File does not exist. Note: your current working directory is /home/user/in-force.**

<details><summary>full result</summary>

```
File does not exist. Note: your current working directory is /home/user/in-force.
```
</details>

### 11. `mcp__inforce__inforce_check`

```json
{
  "text": "Under the Nigeria Tax Act 2025, PAYE in 2026 uses these annual bands: first NGN 800,000 at 0%, next NGN 2,200,000 at 15%, next NGN 9,000,000 at 18%, next NGN 13,000,000 at 21%, next NGN 25,000,000 at 23%, and above NGN 50,000,000 at 25%. Rent relief is 20% of annual rent capped at NGN 500,000. The consolidated relief allowance no longer applies."
}
```

Result: **verdict=STALE claims=9**

<details><summary>full result</summary>

```json
{
  "verdict": "STALE",
  "on": "2026-11-25",
  "items": [
    {
      "line": 1,
      "claim": "Nigeria Tax Act",
      "kind": "citation",
      "ref": "akn/ng/act/2025/7",
      "verdict": "IN_FORCE",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": null,
      "path": [
        "Instrument NTA"
      ],
      "note": "Act or repeal not yet verified",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "first NGN 800,000 at 0%",
      "kind": "figure",
      "ref": "ng.pit.band1.2026",
      "verdict": "IN_FORCE",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": "https://taxsummaries.pwc.com/nigeria/individual",
      "path": [
        "Rule ng.pit.band1.2026",
        "<-SETS- Provision akn/ng/act/2025/7/sec_58",
        "<-CONTAINS- Instrument NTA"
      ],
      "note": "rule not yet verified against the Act's text",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "next NGN 2,200,000 at 15%",
      "kind": "figure",
      "ref": "ng.pit.band2.2026",
      "verdict": "IN_FORCE",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": "https://taxsummaries.pwc.com/nigeria/individual",
      "path": [
        "Rule ng.pit.band2.2026",
        "<-SETS- Provision akn/ng/act/2025/7/sec_58",
        "<-CONTAINS- Instrument NTA"
      ],
      "note": "rule not yet verified against the Act's text",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "next NGN 9,000,000 at 18%",
      "kind": "figure",
      "ref": null,
      "verdict": "NOT_RECOGNISED",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": null,
      "path": [],
      "note": "no pit_band rule in the law pack has this figure",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "next NGN 13,000,000 at 21%",
      "kind": "figure",
      "ref": null,
      "verdict": "NOT_RECOGNISED",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": null,
      "path": [],
      "note": "no pit_band rule in the law pack has this figure",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "next NGN 25,000,000 at 23%",
      "kind": "figure",
      "ref": null,
      "verdict": "NOT_RECOGNISED",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": null,
      "path": [],
      "note": "no pit_band rule in the law pack has this figure",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "above NGN 50,000,000 at 25%",
      "kind": "figure",
      "ref": "ng.pit.top.2026",
      "verdict": "IN_FORCE",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": "https://assets.kpmg.com/content/dam/kpmgsites/xx/pdf/2025/09/fa25-168.pdf.coredownload.inline.pdf",
      "path": [
        "Rule ng.pit.top.2026",
        "<-SETS- Provision akn/ng/act/2025/7/sec_58",
        "<-CONTAINS- Instrument NTA"
      ],
      "note": "rule not yet verified against the Act's text",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "Rent relief",
      "kind": "concept",
      "ref": "ng.pit.rent_relief.2026",
      "verdict": "IN_FORCE",
      "verified": false,
      "endedOn": null,
      "repealedBy": null,
      "successor": null,
      "successorRef": null,
      "successorStatus": null,
      "source": "https://taxsummaries.pwc.com/nigeria/individual/significant-developments",
      "path": [
        "Rule ng.pit.rent_relief.2026",
        "<-SETS- Provision TODO/ng/act/2025/7/sec_rent_relief"
      ],
      "note": "rule not yet verified against the Act's text",
      "mentions": 1
    },
    {
      "line": 1,
      "claim": "consolidated relief allowance",
      "kind": "concept",
      "ref": "ng.pit.cra.old",
      "verdict": "REPEALED",
      "verified": false,
      "endedOn": "2026-01-01",
      "repealedBy": "akn/ng/act/2025/7",
      "successor": "Rent relief: 20% of annual rent, capped at NGN 500,000",
      "successorRef": "ng.pit.rent_relief.2026",
      "successorStatus": "IN_FORCE",
      "source": "https://businessday.ng/?p=1096473",
      "path": [
        "Rule ng.pit.cra.old",
        "<-SETS- Provision TODO/ng/act/pita/sec_cra",
        "<-CONTAINS- Instrument PITA",
        "<-REPEALS 2026-01-01- Instrument NTA"
      ],
      "note": "rule not yet verified against the Act's text",
      "mentions": 1
    }
  ],
  "path": [
    "Rule ng.pit.cra.old <-SETS- Provision TODO/ng/act/pita/sec_cra <-CONTAINS- Instrument PITA <-REPEALS 2026-01-01- Instrument NTA"
  ],
  "unverified": true,
  "disclaimer": "InForce checks whether a provision is in force. It is not legal or tax advice."
}
```
</details>

### 12. `mcp__inforce__inforce_scan`

```json
{
  "path": "demo/_live"
}
```

Result: **verdict=STALE STALE=13 SUSPECT=0 CURRENT=0**

<details><summary>full result</summary>

```json
{
  "verdict": "STALE",
  "on": "2026-11-25",
  "artifacts": [
    {
      "id": "answers/stale_answer.md",
      "kind": "answer",
      "path": "answers/stale_answer.md",
      "line": 1,
      "origin": "scan",
      "status": "STALE",
      "because": [
        {
          "label": "Rule",
          "line": 15,
          "target": "ng.cgt.company.old",
          "text": "capital gains tax at 10%",
          "rule": "Company capital gains taxed at 10%",
          "endedOn": "2026-01-01",
          "successor": "Company gains form part of total profits taxed at 30% (non-small companies)",
          "successorRef": "ng.cgt.company.2026",
          "path": [
            "Rule ng.cgt.company.old",
            "<-SETS- Provision TODO/ng/act/cgta/sec_rate",
            "<-CONTAINS- Instrument CGTA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Instrument",
          "line": 15,
          "target": "TODO/ng/act/cgta",
          "text": "Capital Gains Tax Act",
          "rule": "Capital Gains Tax Act",
          "endedOn": "2026-01-01",
          "successor": "Nigeria Tax Act, 2025",
          "successorRef": "akn/ng/act/2025/7",
          "path": [
            "Instrument CGTA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Rule",
          "line": 11,
          "target": "ng.pit.band2.old",
          "text": "next ₦300,000 at 11%",
          "rule": "PIT: next NGN 300,000 at 11%",
          "endedOn": "2026-01-01",
          "successor": "PIT: next NGN 2,200,000 at 15%",
          "successorRef": "ng.pit.band2.2026",
          "path": [
            "Rule ng.pit.band2.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Rule",
          "line": 11,
          "target": "ng.pit.band1.old",
          "text": "first ₦300,000 is taxed at 7%",
          "rule": "PIT: first NGN 300,000 at 7%",
          "endedOn": "2026-01-01",
          "successor": "PIT: first NGN 800,000 at 0%",
          "successorRef": "ng.pit.band1.2026",
          "path": [
            "Rule ng.pit.band1.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Rule",
          "line": 9,
          "target": "ng.pit.cra.old",
          "text": "Consolidated Relief Allowance",
          "rule": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "endedOn": "2026-01-01",
          "successor": "Rent relief: 20% of annual rent, capped at NGN 500,000",
          "successorRef": "ng.pit.rent_relief.2026",
          "path": [
            "Rule ng.pit.cra.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_cra",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Instrument",
          "line": 8,
          "target": "TODO/ng/act/pita",
          "text": "Personal Income Tax Act",
          "rule": "Personal Income Tax Act",
          "endedOn": "2026-01-01",
          "successor": "Nigeria Tax Act, 2025",
          "successorRef": "akn/ng/act/2025/7",
          "path": [
            "Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        }
      ],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "docs/hr-policy.md",
      "kind": "doc",
      "path": "docs/hr-policy.md",
      "line": 1,
      "origin": "scan",
      "status": "STALE",
      "because": [
        {
          "label": "Rule",
          "line": 6,
          "target": "ng.pit.cra.old",
          "text": "Consolidated Relief Allowance",
          "rule": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "endedOn": "2026-01-01",
          "successor": "Rent relief: 20% of annual rent, capped at NGN 500,000",
          "successorRef": "ng.pit.rent_relief.2026",
          "path": [
            "Rule ng.pit.cra.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_cra",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        },
        {
          "label": "Instrument",
          "line": 4,
          "target": "TODO/ng/act/pita",
          "text": "Personal Income Tax Act",
          "rule": "Personal Income Tax Act",
          "endedOn": "2026-01-01",
          "successor": "Nigeria Tax Act, 2025",
          "successorRef": "akn/ng/act/2025/7",
          "path": [
            "Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        }
      ],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/company_tax.py::CGT_RATE",
      "kind": "code",
      "path": "payroll/company_tax.py",
      "line": 3,
      "origin": "scan",
      "status": "STALE",
      "because": [
        {
          "label": "Rule",
          "line": 3,
          "target": "ng.cgt.company.old",
          "text": "CGT_RATE",
          "rule": "Company capital gains taxed at 10%",
          "endedOn": "2026-01-01",
          "successor": "Company gains form part of total profits taxed at 30% (non-small companies)",
          "successorRef": "ng.cgt.company.2026",
          "path": [
            "Rule ng.cgt.company.old",
            "<-SETS- Provision TODO/ng/act/cgta/sec_rate",
            "<-CONTAINS- Instrument CGTA",
            "<-REPEALS 2026-01-01- Instrument NTA"
          ]
        }
      ],
      "via": [],
      "alsoCheck": [
        "payroll/company_tax.py::capital_gains_tax",
        "tests/test_company_tax.py"
      ],
      "chain": []
    },
    {
      "id": "payroll/paye.py::CRA_FLAT_MIN",
      "ki
... (truncated; full text in the .jsonl)
```
</details>

**Claude:** I've stopped before editing anything. InForce doesn't hold enough of the new tax table to rewrite `paye.py` without me making up figures, which CLAUDE.md forbids ("Never invent law"). No files are changed so far.

## Brief on `payroll/paye.py`: **STALE** (as of 2026-11-25)

Every rule below comes from the law pack but is marked `verified: false`, so it is still unverified.

| Artifact | Old rule (repealed 2026-01-01) | Successor InForce returns | Provision |
|---|---|---|---|
| `PIT_BANDS_2025` (line 4) | `ng.pit.band1.old`: first ₦300,000 at 7% | `ng.pit.band1.2026`: first ₦800,000 at 0% | `akn/ng/act/2025/7/sec_58` |
| `PIT_BANDS_2025` (line 4) | `ng.pit.band2.old`: next ₦300,000 at 11% | `ng.pit.band2.2026`: next ₦2,200,000 at 15% | `akn/ng/act/2025/7/sec_58` |
| `CRA_RATE`, `CRA_FLAT_MIN` (lines 14–15) | `ng.pit.cra.old`: 20% of gross plus the higher of ₦200k or 1% | `ng.pit.rent_relief.2026`: 20% of annual rent, capped at ₦500,000 | `TODO/ng/act/2025/7/sec_rent_relief` (no section number yet) |

The proof for each old rule runs Rule → `PITA` section → `PITA` ← REPEALS 2026-01-01 ← `NTA`. `consolidated_relief` and `compute_paye` are STALE because they use those constants. The brief's re-check list (it has no section headed "also check") points to `payroll/payslip.py::build_payslip` and `tests/test_paye.py`.

## Why I stopped

1. **The tax bands are incomplete.** I ran `inforce_check` on the full 2026 band table. The law pack only knows the first band (`band1.2026`), the second (`band2.2026`) and the top rate, ₦50M and above at 25% (`ng.pit.top.2026`, same section 58). The three middle bands (₦9M at 18%, ₦13M at 21%, ₦25M at 23%) came back NOT_RECOGNISED. Writing them from memory would be inventing law, and leaving them out gives wrong PAYE for anyone with taxable income between ₦3M and ₦50M.
2. **Rent relief changes the function's inputs.** Relief now depends on annual rent, not gross pay. `compute_paye(gross)` needs a new `annual_rent` argument, which also changes `build_payslip`.
3. **There is more stale material than this file.** The scan of `demo/_live` also flags `payroll/company_tax.py::CGT_RATE` (needs `ng.cgt.company.2026`) and its test, `docs/hr-policy.md`, `templates/payslip.html` and `answers/stale_answer.md`. You asked for zero STALE, but that's outside the PAYE work you described.

Two tool calls were also blocked by permission mode: a Bash read and a direct read-only Cypher query to the law pack. I couldn't list the rule files any other way.

## Options

- **A (my recommendation):** you add rule entries for bands 3–5 to `data/rules/*.yaml` (still `verified: false`) and rebuild the law pack. Then I make every change, cite every rule, and scan until it reports zero STALE.
- **B:** I write only the rules InForce returns (bands 1, 2 and the top rate, plus rent relief). `compute_paye` would refuse taxable income between ₦3M and ₦50M with a clear error, and the tests would only cover incomes the known bands fully determine.
- **C:** you give me the middle bands and I use them as written, marked as your input rather than InForce's.

Please also tell me whether the zero-STALE goal covers `company_tax.py`, the docs, the template and the stale answer, or just the PAYE files.

---
*InForce checks whether a provision is in force. It is not legal or tax advice.*

---

Finished: `success`, 13 turns, 40s, $0.39.

