# Agent session: Claude Code fixes a payroll repo through InForce

Recorded 25 November 2026. Headless Claude Code (2.1.332, model `claude-opus-5-5`) worked on a
throwaway copy of the synthetic demo repo (`demo/_live`, deleted afterwards) through the InForce
MCP tools. It took the stale scan from **13 STALE artifacts to 0**, in 24 turns, 61 s, $0.61.
Recording: [agent-session.gif](agent-session.gif) / [agent-session.mp4](agent-session.mp4) / [agent-session.cast](agent-session.cast).
Raw event log: [agent-session.jsonl](agent-session.jsonl). How it was made: [README.md](README.md).

## Prompt

> Use the inforce MCP tools. First call inforce_brief on demo/_live/payroll/paye.py and summarise the verdict. Then fix paye.py and its test so they follow the successor rules InForce returns, and update any other files it lists under 'also check'. After each change, run inforce_scan on demo/_live until it reports zero STALE artifacts. Do not touch demo/naira-payroll, do not commit, and cite the provisions InForce returns. Zero STALE means every file the scan flags in demo/_live, including payroll/company_tax.py and its test, docs/hr-policy.md and templates/payslip.html; rewrite answers/stale_answer.md to current law rather than deleting it.

## Scans during the session

| After | STALE | SUSPECT | CURRENT |
|---|---:|---:|---:|
| start (`inforce_scan`, step 4) | 13 | 0 | 0 |
| `paye.py`, `payslip.py`, `test_paye.py` (step 16) | 6 | 3 | 4 |
| `company_tax.py` and its test (step 19) | 3 | 3 | 6 |
| `hr-policy.md`, `payslip.html`, `stale_answer.md` (step 23) | **0** | 6 | 6 |

SUSPECT means the artifact now rests on 2026 rules that are still `verified: false` in the law pack.

## Checked independently after the session

- **Figures:** every one written into the code (the six NTA s. 58 bands, rent relief at 20% capped at ₦500,000, company profits at 30%) is a rule InForce returned. Each cites its rule id or provision.
- **Tests:** the copy's own tests pass: `python -m pytest -q` in `demo/_live` gave 7 passed. The agent could not run them itself, because Bash was outside its allow-list.
- **Original untouched:** `demo/naira-payroll` was byte-for-byte unchanged (sha256 of every file before and after).
- **Final scan:** `inforce scan demo/_live` (CLI) reported:

```
demo/_live on 2026-11-25: SUSPECT  (0 rest on repealed law, 0 use or test them, 6 suspect, 6 current)
SUSPECT (rests on unverified or unrecognised law): answers/stale_answer.md, docs/hr-policy.md, payroll/paye.py::PIT_BANDS_2026,
payroll/paye.py::RENT_RELIEF_CAP, payroll/paye.py::RENT_RELIEF_RATE, templates/payslip.html
exit=0
```

**Points to note:**
- **Rent relief:** InForce lists rent relief as *related to* the dropped CRA, not as its successor. The agent says that using it in `compute_paye` was its own choice.
- **Unlinked company constant:** the agent renamed `CGT_RATE` to `COMPANY_PROFITS_TAX_RATE`, which no scan pattern matches yet. That constant is CURRENT with no law link, rather than SUSPECT.

## Transcript (every tool call and result)

- Session model: `claude-opus-5-5`; Claude Code 2.1.332
- MCP tools available: `mcp__inforce__inforce_brief`, `mcp__inforce__inforce_check`, `mcp__inforce__inforce_scan`, `mcp__relate-law__get_schema`, `mcp__relate-law__read_cypher`

### 1. `ToolSearch`

```json
{
  "query": "select:mcp__inforce__inforce_brief,mcp__inforce__inforce_check,mcp__inforce__inforce_scan"
}
```

### 2. `mcp__inforce__inforce_brief`

```json
{
  "target": "demo/_live/payroll/paye.py",
  "repo": "demo/_live"
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
      "was": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
      "ref": "ng.pit.cra.old",
      "refs": [
        "ng.pit.cra.old"
      ],
      "endedOn": "2026-01-01",
      "now": null,
      "nowRef": null,
      "scale": null,
      "related": [
        {
          "id": "ng.pit.rent_relief.2026",
          "text": "Rent relief: 20% of annual rent, capped at NGN 500,000"
        }
      ]
    },
    {
      "was": "PIT: first NGN 300,000 at 7%; PIT: next NGN 300,000 at 11%",
      "ref": "ng.pit.band1.old",
      "refs": [
        "ng.pit.band1.old",
        "ng.pit.band2.old"
      ],
      "endedOn": "2026-01-01",
      "now": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
      "nowRef": "akn/ng/act/2025/7/sec_58",
      "scale": [
        {
          "id": "ng.pit.band1.2026",
          "text": "PIT: first NGN 800,000 at 0%",
          "value": 0.0,
          "verified": false
        },
        {
          "id": "ng.pit.band2.2026",
          "text": "PIT: next NGN 2,200,000 at 15%",
          "value": 0.15,
          "verified": false
        },
        {
          "id": "ng.pit.band3.2026",
          "text": "PIT: next NGN 9,000,000 at 18%",
          "value": 0.18,
          "verified": false
        },
        {
          "id": "ng.pit.band4.2026",
          "text": "PIT: next NGN 13,000,000 at 21%",
          "value": 0.21,
          "verified": false
        },
        {
          "id": "ng.pit.band5.2026",
          "text": "PIT: next NGN 25,000,000 at 23%",
          "value": 0.23,
          "verified": false
        },
        {
          "id": "ng.pit.top.2026",
          "text": "PIT: income over NGN 50,000,000 at 25%",
          "value": 0.25,
          "verified": false
        }
      ],
      "related": []
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
        "<-REPEALS 2026-01-01- Instrument NTA",
        "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
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
        "<-REPEALS 2026-01-01- Instrument NTA",
        "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
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
          "was": "PIT: first NGN 300,000 at 7%; PIT: next NGN 300,000 at 11%",
          "now": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "nowRef": "akn/ng/act/2025/7/sec_58",
          "related": []
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
          "now": null,
          "nowRef": null,
          "related": [
            {
              "id": "ng.pit.rent_relief.2026",
              "text": "Rent relief: 20% of annual rent, capped at NGN 500,000"
            }
          ]
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
          "now": null,
          "nowRef": null,
          "related": [
            {
              "id": "ng.pit.rent_relief.2026",
              "text": "Rent relief: 20% of annual rent, capped at NGN 500,000"
            }
          ]
        }
      ]
    },
    {
      "where": "payroll/paye.py:18",
... (truncated; full text in the .jsonl)
```
</details>

### 3. `Bash`

```json
{
  "command": "cd /home/user/in-force/demo/_live && find . -type f -not -path './.inforce/*' | sort && git -C /home/user/in-force status --short demo/_live | head",
  "description": "List files in the live demo folder"
}
```

Result (error): **Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.**

<details><summary>full result</summary>

```
Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.
```
</details>

### 4. `mcp__inforce__inforce_scan`

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
          "scale": null,
          "related": [],
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
          "scale": null,
          "related": [],
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
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band2.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 11,
          "target": "ng.pit.band1.old",
          "text": "first ₦300,000 is taxed at 7%",
          "rule": "PIT: first NGN 300,000 at 7%",
          "endedOn": "2026-01-01",
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band1.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 9,
          "target": "ng.pit.cra.old",
          "text": "Consolidated Relief Allowance",
          "rule": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "endedOn": "2026-01-01",
          "successor": null,
          "successorRef": null,
          "scale": null,
          "related": [
            {
              "id": "ng.pit.rent_relief.2026",
              "text": "Rent relief: 20% of 
... (truncated; full text in the .jsonl)
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

### 8. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/payroll/company_tax.py"
}
```

Result: **1	"""Company tax helpers. SYNTHETIC DEMO CODE, written as of 2025."""**

<details><summary>full result</summary>

```
1	"""Company tax helpers. SYNTHETIC DEMO CODE, written as of 2025."""
2	
3	CGT_RATE = 0.10
4	
5	
6	def capital_gains_tax(gain: float) -> float:
7	    """Tax on a company's chargeable gain, charged separately from income tax."""
8	    return round(max(0.0, gain) * CGT_RATE, 2)
9	
```
</details>

### 9. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/tests/test_company_tax.py"
}
```

Result: **1	"""SYNTHETIC DEMO."""**

<details><summary>full result</summary>

```
1	"""SYNTHETIC DEMO."""
2	
3	from payroll.company_tax import capital_gains_tax
4	
5	
6	def test_gain_on_building():
7	    assert capital_gains_tax(50_000_000) == 5_000_000.0
8	
```
</details>

### 10. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/docs/hr-policy.md"
}
```

Result: **1	<!-- SYNTHETIC DEMO DOCUMENT for a made-up employer. -->**

<details><summary>full result</summary>

```
1	<!-- SYNTHETIC DEMO DOCUMENT for a made-up employer. -->
2	# Payroll policy: PAYE
3	
4	PAYE is deducted every month under the Personal Income Tax Act.
5	
6	Before tax, each employee receives the Consolidated Relief Allowance on their
7	annual gross income. The relief is applied automatically by the payroll system;
8	employees do not need to claim it.
9	
10	Questions go to the payroll team.
11	
```
</details>

### 11. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/templates/payslip.html"
}
```

Result: **1	<!-- SYNTHETIC DEMO TEMPLATE -->**

<details><summary>full result</summary>

```
1	<!-- SYNTHETIC DEMO TEMPLATE -->
2	<html>
3	  <body>
4	    <h1>Payslip: {{ employee }}</h1>
5	    <table>
6	      <tr><td>Gross</td><td>{{ gross }}</td></tr>
7	      <tr><td>PAYE</td><td>{{ paye }}</td></tr>
8	      <tr><td>Net</td><td>{{ net }}</td></tr>
9	    </table>
10	    <footer>Tax computed under PITA.</footer>
11	  </body>
12	</html>
13	
```
</details>

### 12. `Read`

```json
{
  "file_path": "/home/user/in-force/demo/_live/answers/stale_answer.md"
}
```

Result: **1	<!-- SYNTHETIC DEMO DATA. A made-up chatbot answer written as of 2025, before**

<details><summary>full result</summary>

```
1	<!-- SYNTHETIC DEMO DATA. A made-up chatbot answer written as of 2025, before
2	     the 2026 tax reform. Not advice; deliberately out of date. -->
3	
4	**Q:** How is PAYE worked out for a Lagos employee, and what tax does a company pay when it sells a building at a gain?
5	
6	**A (assistant, 2025):**
7	
8	PAYE is computed under the Personal Income Tax Act (PITA). First deduct the
9	Consolidated Relief Allowance (CRA): 20% of gross income plus the higher of
10	₦200,000 or 1% of gross income. Then apply the graduated bands to what is left:
11	the first ₦300,000 is taxed at 7%, and the next ₦300,000 at 11%, rising band by
12	band after that.
13	
14	For the company, the gain on the building is not part of its income tax. It is
15	charged separately under the Capital Gains Tax Act, and companies pay capital
16	gains tax at 10% of the chargeable gain.
17	
```
</details>

**Claude:** The brief came back **STALE** for `paye.py`. I'll write the fixes now, using the successor rules InForce returned.

### 13. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/payroll/paye.py",
  "content": "\"\"\"PAYE for monthly payroll. SYNTHETIC DEMO CODE, updated for the law in force from 1 Jan 2026.\n\nSource: Nigeria Tax Act 2025, s. 58 + Fourth Schedule (akn/ng/act/2025/7/sec_58).\nRule values come from the InForce law pack and are still marked unverified there.\n\"\"\"\n\n# Annual taxable-income bands: (width of band in NGN, rate). Last band is open-ended.\n# NTA s. 58 + Fourth Schedule (ng.pit.band1.2026 .. ng.pit.top.2026).\nPIT_BANDS_2026 = (\n    (800_000, 0.00),\n    (2_200_000, 0.15),\n    (9_000_000, 0.18),\n    (13_000_000, 0.21),\n    (25_000_000, 0.23),\n    (None, 0.25),\n)\n\n# Rent relief (ng.pit.rent_relief.2026): 20% of annual rent paid, capped at NGN 500,000.\nRENT_RELIEF_RATE = 0.20\nRENT_RELIEF_CAP = 500_000\n\n\ndef rent_relief(annual_rent: float) -> float:\n    \"\"\"Relief deducted from annual gross income for rent the employee pays.\"\"\"\n    return min(RENT_RELIEF_RATE * max(0.0, annual_rent), RENT_RELIEF_CAP)\n\n\ndef compute_paye(gross: float, annual_rent: float = 0.0) -> float:\n    \"\"\"Annual PAYE on an annual gross income, in NGN.\"\"\"\n    taxable = max(0.0, gross - rent_relief(annual_rent))\n    tax = 0.0\n    for width, rate in PIT_BANDS_2026:\n        if width is None or taxable <= width:\n            tax += taxable * rate\n            break\n        tax += width * rate\n        taxable -= width\n    return round(tax, 2)\n"
}
```

Result: **The file /home/user/in-force/demo/_live/payroll/paye.py has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/payroll/paye.py has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 14. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/tests/test_paye.py",
  "content": "\"\"\"Tests pinned to the law in force from 1 Jan 2026 (NTA s. 58 + Fourth Schedule). SYNTHETIC DEMO.\"\"\"\n\nfrom payroll.paye import compute_paye, rent_relief\n\n\ndef test_first_band_is_zero_rated():\n    # first NGN 800,000 at 0%\n    assert compute_paye(800_000) == 0.0\n\n\ndef test_mid_income_no_rent():\n    # gross 3,000,000, no rent: taxable 3,000,000\n    # 800k@0% + 2,200k@15% = 0 + 330,000\n    assert compute_paye(3_000_000) == 330_000.0\n\n\ndef test_rent_relief_reduces_taxable_income():\n    # rent 1,200,000: relief 20% = 240,000; taxable 2,760,000\n    # 800k@0% + 1,960k@15% = 294,000\n    assert rent_relief(1_200_000) == 240_000.0\n    assert compute_paye(3_000_000, annual_rent=1_200_000) == 294_000.0\n\n\ndef test_rent_relief_is_capped():\n    assert rent_relief(5_000_000) == 500_000\n    # taxable 2,500,000: 1,700k@15% = 255,000\n    assert compute_paye(3_000_000, annual_rent=5_000_000) == 255_000.0\n\n\ndef test_top_band():\n    # gross 60,000,000: 0 + 330,000 + 1,620,000 + 2,730,000 + 5,750,000 + 10,000k@25% (2,500,000)\n    assert compute_paye(60_000_000) == 12_930_000.0\n"
}
```

Result: **The file /home/user/in-force/demo/_live/tests/test_paye.py has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/tests/test_paye.py has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 15. `Edit`

```json
{
  "replace_all": false,
  "file_path": "/home/user/in-force/demo/_live/payroll/payslip.py",
  "old_string": "def build_payslip(employee_id: str, annual_gross: float) -> dict:\n    \"\"\"Figures for one month's payslip. employee_id is a made-up identifier.\"\"\"\n    annual_tax = compute_paye(annual_gross)",
  "new_string": "def build_payslip(employee_id: str, annual_gross: float, annual_rent: float = 0.0) -> dict:\n    \"\"\"Figures for one month's payslip. employee_id is a made-up identifier.\"\"\"\n    annual_tax = compute_paye(annual_gross, annual_rent)"
}
```

Result: **The file /home/user/in-force/demo/_live/payroll/payslip.py has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/payroll/payslip.py has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 16. `mcp__inforce__inforce_scan`

```json
{
  "path": "demo/_live"
}
```

Result: **verdict=STALE STALE=6 SUSPECT=3 CURRENT=4**

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
          "scale": null,
          "related": [],
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
          "scale": null,
          "related": [],
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
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band2.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 11,
          "target": "ng.pit.band1.old",
          "text": "first ₦300,000 is taxed at 7%",
          "rule": "PIT: first NGN 300,000 at 7%",
          "endedOn": "2026-01-01",
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band1.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 9,
          "target": "ng.pit.cra.old",
          "text": "Consolidated Relief Allowance",
          "rule": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "endedOn": "2026-01-01",
          "successor": null,
          "successorRef": null,
          "scale": null,
          "related": [
            {
              "id": "ng.pit.rent_relief.2026",
              "text": "Rent relief: 20% of 
... (truncated; full text in the .jsonl)
```
</details>

**Claude:** `paye.py`, `payslip.py` and `test_paye.py` no longer show as STALE. The new constants show as SUSPECT because the 2026 rules are still unverified. Next is company tax.

### 17. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/payroll/company_tax.py",
  "content": "\"\"\"Company tax helpers. SYNTHETIC DEMO CODE, updated for the law in force from 1 Jan 2026.\n\nSource: Nigeria Tax Act 2025 (akn/ng/act/2025/7), rule ng.cgt.company.2026: a company's\nchargeable gains form part of its total profits, taxed at 30% for non-small companies.\nThe rule is still marked unverified in the InForce law pack. Small companies are not modelled.\n\"\"\"\n\nCOMPANY_PROFITS_TAX_RATE = 0.30\n\n\ndef tax_on_chargeable_gain(gain: float) -> float:\n    \"\"\"Tax due on a non-small company's chargeable gain, taxed as part of total profits.\"\"\"\n    return round(max(0.0, gain) * COMPANY_PROFITS_TAX_RATE, 2)\n"
}
```

Result: **The file /home/user/in-force/demo/_live/payroll/company_tax.py has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/payroll/company_tax.py has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 18. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/tests/test_company_tax.py",
  "content": "\"\"\"Tests pinned to the law in force from 1 Jan 2026 (ng.cgt.company.2026). SYNTHETIC DEMO.\"\"\"\n\nfrom payroll.company_tax import tax_on_chargeable_gain\n\n\ndef test_gain_on_building_taxed_with_profits():\n    # non-small company: gain forms part of total profits at 30%\n    assert tax_on_chargeable_gain(50_000_000) == 15_000_000.0\n\n\ndef test_loss_pays_nothing():\n    assert tax_on_chargeable_gain(-1_000) == 0.0\n"
}
```

Result: **The file /home/user/in-force/demo/_live/tests/test_company_tax.py has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/tests/test_company_tax.py has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 19. `mcp__inforce__inforce_scan`

```json
{
  "path": "demo/_live"
}
```

Result: **verdict=STALE STALE=3 SUSPECT=3 CURRENT=6**

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
          "scale": null,
          "related": [],
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
          "scale": null,
          "related": [],
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
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band2.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 11,
          "target": "ng.pit.band1.old",
          "text": "first ₦300,000 is taxed at 7%",
          "rule": "PIT: first NGN 300,000 at 7%",
          "endedOn": "2026-01-01",
          "successor": "NTA s. 58 + Fourth Schedule (whole scale): PIT: first NGN 800,000 at 0% · PIT: next NGN 2,200,000 at 15% · PIT: next NGN 9,000,000 at 18% · PIT: next NGN 13,000,000 at 21% · PIT: next NGN 25,000,000 at 23% · PIT: income over NGN 50,000,000 at 25%",
          "successorRef": "akn/ng/act/2025/7/sec_58",
          "scale": [
            {
              "id": "ng.pit.band1.2026",
              "text": "PIT: first NGN 800,000 at 0%",
              "value": 0.0,
              "verified": false
            },
            {
              "id": "ng.pit.band2.2026",
              "text": "PIT: next NGN 2,200,000 at 15%",
              "value": 0.15,
              "verified": false
            },
            {
              "id": "ng.pit.band3.2026",
              "text": "PIT: next NGN 9,000,000 at 18%",
              "value": 0.18,
              "verified": false
            },
            {
              "id": "ng.pit.band4.2026",
              "text": "PIT: next NGN 13,000,000 at 21%",
              "value": 0.21,
              "verified": false
            },
            {
              "id": "ng.pit.band5.2026",
              "text": "PIT: next NGN 25,000,000 at 23%",
              "value": 0.23,
              "verified": false
            },
            {
              "id": "ng.pit.top.2026",
              "text": "PIT: income over NGN 50,000,000 at 25%",
              "value": 0.25,
              "verified": false
            }
          ],
          "related": [],
          "path": [
            "Rule ng.pit.band1.old",
            "<-SETS- Provision TODO/ng/act/pita/sec_bands",
            "<-CONTAINS- Instrument PITA",
            "<-REPEALS 2026-01-01- Instrument NTA",
            "-SUCCEEDED_BY-> Provision akn/ng/act/2025/7/sec_58"
          ]
        },
        {
          "label": "Rule",
          "line": 9,
          "target": "ng.pit.cra.old",
          "text": "Consolidated Relief Allowance",
          "rule": "CRA: 20% of gross income plus the higher of NGN 200,000 or 1% of gross",
          "endedOn": "2026-01-01",
          "successor": null,
          "successorRef": null,
          "scale": null,
          "related": [
            {
              "id": "ng.pit.rent_relief.2026",
              "text": "Rent relief: 20% of 
... (truncated; full text in the .jsonl)
```
</details>

**Claude:** Company tax is now CURRENT. Next are the three documents.

### 20. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/docs/hr-policy.md",
  "content": "<!-- SYNTHETIC DEMO DOCUMENT for a made-up employer. -->\n# Payroll policy: PAYE\n\nPAYE is deducted every month under the Nigeria Tax Act, 2025, which has been in\nforce since 1 January 2026. The graduated rates come from section 58 and the\nFourth Schedule: the first ₦800,000 of annual taxable income is taxed at 0%.\n\nEmployees who pay rent can get rent relief of 20% of their annual rent, up to\n₦500,000. To claim it, give the payroll team your annual rent and supporting\ndocuments. Payroll deducts the relief from annual gross income before tax.\n\nQuestions go to the payroll team.\n"
}
```

Result: **The file /home/user/in-force/demo/_live/docs/hr-policy.md has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/docs/hr-policy.md has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 21. `Edit`

```json
{
  "replace_all": false,
  "file_path": "/home/user/in-force/demo/_live/templates/payslip.html",
  "old_string": "Tax computed under PITA.",
  "new_string": "Tax computed under the Nigeria Tax Act, 2025 (s. 58 and Fourth Schedule)."
}
```

Result: **The file /home/user/in-force/demo/_live/templates/payslip.html has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/templates/payslip.html has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 22. `Write`

```json
{
  "file_path": "/home/user/in-force/demo/_live/answers/stale_answer.md",
  "content": "<!-- SYNTHETIC DEMO DATA. A made-up chatbot answer, rewritten to the law in force\n     on 25 November 2026 using InForce. Rule values are still unverified in the\n     InForce law pack. Not legal or tax advice. -->\n\n**Q:** How is PAYE worked out for a Lagos employee, and what tax does a company pay when it sells a building at a gain?\n\n**A (assistant, updated 25 November 2026):**\n\nFrom 1 January 2026, PAYE is computed under the Nigeria Tax Act, 2025. Employees\nwho pay rent can deduct rent relief: 20% of their annual rent, up to ₦500,000.\nThen apply the graduated scale in section 58 and the Fourth Schedule. The first\n₦800,000 is taxed at 0%. The next ₦2,200,000 is taxed at 15%, the next ₦9,000,000\nat 18%, the next ₦13,000,000 at 21% and the next ₦25,000,000 at 23%. Income above\n₦50,000,000 is taxed at 25%.\n\nFor the company, the gain on the building is now part of its total profits. A\ncompany that is not a small company pays tax on those profits at 30%.\n"
}
```

Result: **The file /home/user/in-force/demo/_live/answers/stale_answer.md has been updated successfully. (file state is current in your context — no need to Read it back)**

<details><summary>full result</summary>

```
The file /home/user/in-force/demo/_live/answers/stale_answer.md has been updated successfully. (file state is current in your context — no need to Read it back)
```
</details>

### 23. `mcp__inforce__inforce_scan`

```json
{
  "path": "demo/_live"
}
```

Result: **verdict=SUSPECT STALE=0 SUSPECT=6 CURRENT=6**

<details><summary>full result</summary>

```json
{
  "verdict": "SUSPECT",
  "on": "2026-11-25",
  "artifacts": [
    {
      "id": "answers/stale_answer.md",
      "kind": "answer",
      "path": "answers/stale_answer.md",
      "line": 1,
      "origin": "scan",
      "status": "SUSPECT",
      "because": [],
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
      "status": "SUSPECT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/paye.py::PIT_BANDS_2026",
      "kind": "code",
      "path": "payroll/paye.py",
      "line": 9,
      "origin": "scan",
      "status": "SUSPECT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/paye.py::RENT_RELIEF_CAP",
      "kind": "code",
      "path": "payroll/paye.py",
      "line": 20,
      "origin": "scan",
      "status": "SUSPECT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/paye.py::RENT_RELIEF_RATE",
      "kind": "code",
      "path": "payroll/paye.py",
      "line": 19,
      "origin": "scan",
      "status": "SUSPECT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "templates/payslip.html",
      "kind": "template",
      "path": "templates/payslip.html",
      "line": 1,
      "origin": "scan",
      "status": "SUSPECT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/company_tax.py::tax_on_chargeable_gain",
      "kind": "code",
      "path": "payroll/company_tax.py",
      "line": 11,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/paye.py::compute_paye",
      "kind": "code",
      "path": "payroll/paye.py",
      "line": 28,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/paye.py::rent_relief",
      "kind": "code",
      "path": "payroll/paye.py",
      "line": 23,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "payroll/payslip.py::build_payslip",
      "kind": "code",
      "path": "payroll/payslip.py",
      "line": 6,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "tests/test_company_tax.py",
      "kind": "test",
      "path": "tests/test_company_tax.py",
      "line": 1,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    },
    {
      "id": "tests/test_paye.py",
      "kind": "test",
      "path": "tests/test_paye.py",
      "line": 1,
      "origin": "scan",
      "status": "CURRENT",
      "because": [],
      "via": [],
      "alsoCheck": [],
      "chain": []
    }
  ],
  "path": [],
  "disclaimer": "InForce checks whether a provision is in force. It is not legal or tax advice.",
  "store": "/home/user/in-force/demo/_live/.inforce/project.rl",
  "warnings": []
}
```
</details>

**Claude:** The last `inforce_scan` on `demo/_live` reports **zero STALE artifacts**. The overall verdict is now **SUSPECT**, not CURRENT: 6 artifacts are SUSPECT and the other 6 are CURRENT. I couldn't run pytest because Bash is denied in this session, so the new tests haven't been run. I didn't touch `demo/naira-payroll` and made no commits.

## What the brief said about `payroll/paye.py`
The verdict was **STALE**. Everything in the file rested on the Personal Income Tax Act (PITA), which the Nigeria Tax Act 2025 (NTA) repealed on 2026-01-01.
- **`PIT_BANDS_2025`** (line 4) used the old bands `ng.pit.band1.old` and `ng.pit.band2.old` (₦300k at 7%, then ₦300k at 11%). They were replaced by **NTA s. 58 and the Fourth Schedule** (`akn/ng/act/2025/7/sec_58`): ₦800k at 0%, the next ₦2.2M at 15%, ₦9M at 18%, ₦13M at 21% and ₦25M at 23%, then 25% on income over ₦50M.
- **`CRA_RATE` and `CRA_FLAT_MIN`** (lines 14–15) came from the old relief rule `ng.pit.cra.old`. InForce gives **no direct successor** for it; it only lists a related rule, **`ng.pit.rent_relief.2026`**: 20% of annual rent, capped at ₦500,000.
- Because of these, `consolidated_relief`, `compute_paye`, `payroll/payslip.py::build_payslip` and `tests/test_paye.py` were STALE too.

## Changes, with a scan after each step
1. **`payroll/paye.py`**: the bands are now `PIT_BANDS_2026`, taken from s. 58. I removed the old relief and added `rent_relief()`. `compute_paye(gross, annual_rent=0.0)` now applies rent relief.
   **`payroll/payslip.py`**: `build_payslip` passes an optional `annual_rent` through.
   **`tests/test_paye.py`**: the expected values now follow the new scale, for example gross ₦3M gives ₦330,000. I added tests for the rent relief cap and the top band.
   → The PAYE files cleared.
2. **`payroll/company_tax.py`**: `CGT_RATE` (10%, `ng.cgt.company.old`) is replaced by `COMPANY_PROFITS_TAX_RATE = 0.30`, following **`ng.cgt.company.2026`**: company gains are taxed as part of total profits at 30% for non-small companies. I renamed the function to `tax_on_chargeable_gain`.
   **`tests/test_company_tax.py`**: a ₦50M gain now gives ₦15M tax.
   → Company tax cleared.
3. **`docs/hr-policy.md`**, **`templates/payslip.html`** and **`answers/stale_answer.md`**: these now cite the Nigeria Tax Act 2025, s. 58 and Fourth Schedule, plus rent relief and the 30% rule. I rewrote the answer to current law rather than deleting it.
   → STALE count reached 0.

## Things to check
- **The new rules are unverified.** InForce marks every 2026 rule `verified: false`. That's why `PIT_BANDS_2026`, `RENT_RELIEF_RATE`, `RENT_RELIEF_CAP`, the hr-policy doc, the payslip template and the answer show SUSPECT. The scan didn't list a reason for these, so I'm assuming unverified rules are the cause. They need checking against the Act's text.
- **Rent relief is my choice.** InForce returned it as related to the old relief, not as its successor. Treating it as the replacement and adding the `annual_rent` parameter was my decision.
- **Small companies aren't handled.** InForce gave a rate only for non-small companies, so the code covers that case only and says so.
- **The new company tax constant isn't tracked.** `COMPANY_PROFITS_TAX_RATE` didn't appear as an artifact in the scan, so nothing links it to `ng.cgt.company.2026` yet.

InForce checks whether a provision is in force. It is not legal or tax advice.

---

Finished: `success`, 24 turns, 61s, $0.61.

