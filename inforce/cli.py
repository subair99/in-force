"""InForce command line. Built with Relate."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import law, loader
from .check import DISCLAIMER, check_text
from .paths import LAW_PACK, RULES_DIR
from .store import StoreLocked, open_store

EXIT_STALE = 3

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Find answers, code and documents that still run on repealed law. Built with Relate.")
console = Console()
err = Console(stderr=True)

VERDICT_STYLE = {
    "REPEALED": "bold red", "STALE": "bold red", "FELL": "bold red",
    "SAVED": "yellow", "SUSPECT": "yellow", "NOT_YET": "yellow", "NOT_RECOGNISED": "magenta",
    "IN_FORCE": "green", "CURRENT": "green", "STANDS": "green",
}

ON_HELP = "Date to check against (YYYY-MM-DD). Default: today."
LAW_HELP = "Law pack .rl file."


def _on(value: str | None) -> str:
    if value is None:
        return dt.date.today().isoformat()
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        err.print(f"[red]--on must be a date like 2026-03-01, got {value!r}[/red]")
        raise typer.Exit(1) from None


def _v(verdict: str) -> str:
    style = VERDICT_STYLE.get(verdict, "")
    return f"[{style}]{verdict}[/{style}]" if style else verdict


def _log(msg: str) -> None:
    err.print(f"[yellow]{msg}[/yellow]", soft_wrap=True)


def _locked(exc: StoreLocked) -> typer.Exit:
    err.print(f"[red]{exc}[/red]")
    return typer.Exit(StoreLocked.exit_code)


def footer() -> None:
    console.print(f"\n[dim]{DISCLAIMER}[/dim]")


@app.callback()
def main() -> None:
    """InForce: is it still law?"""


@app.command()
def load(
    allow_unverified: bool = typer.Option(False, "--allow-unverified",
                                          help="Load law entries a human has not yet verified."),
    rules: Path = typer.Option(RULES_DIR, help="Directory of rule YAML files."),
    out: Path = typer.Option(LAW_PACK, help="Law pack .rl file to (re)build."),
    force: bool = typer.Option(False, "--force", help="Rebuild even if the pack is up to date."),
    embed: bool = typer.Option(True, "--embed/--no-embed", help="Store rule embeddings for `ask` (model2vec)."),
) -> None:
    """Build the law pack .rl from the rule YAML files (skipped when already up to date)."""
    try:
        report = loader.load(rules, out, allow_unverified=allow_unverified, log=_log, force=force, embed=embed)
    except loader.UnverifiedLaw as exc:
        err.print(f"[red]Refusing to load: {exc}[/red]")
        for e in exc.entries[:15]:
            err.print(f"  - {e}")
        if len(exc.entries) > 15:
            err.print(f"  ... and {len(exc.entries) - 15} more (see `inforce verify`)")
        raise typer.Exit(1) from None
    except loader.BadReference as exc:
        err.print(f"[red]Bad reference in rule YAML: {exc}[/red]")
        raise typer.Exit(1) from None
    except StoreLocked as exc:
        raise _locked(exc) from None

    if report.skipped:
        console.print(f"[dim]Law pack {report.path} is up to date with the rule YAML; not rebuilt "
                      "(use --force to rebuild).[/dim]")
    table = Table(title=f"Law pack: {report.path}")
    table.add_column("label")
    table.add_column("nodes", justify="right")
    for label, n in report.counts.items():
        table.add_row(label, str(n))
    console.print(table)
    if report.unverified:
        console.print(f"[bold yellow]UNVERIFIED:[/bold yellow] {len(report.unverified)} law entries are not yet "
                      "checked against the Act's text. Verdicts built on them are provisional.")
    for s in report.stubs:
        console.print(f"[yellow]stub[/yellow] {s}")
    for w in report.warnings:
        console.print(f"[yellow]warning[/yellow] {w}")
    footer()


_PATH_SUFFIXES = (".md", ".txt", ".py", ".html", ".htm", ".json", ".yaml", ".yml", ".csv", ".rst")


def _looks_like_path(target: str) -> bool:
    """One word with a path separator or a document suffix: a mistyped file name, not text to check."""
    if not target or any(ch.isspace() for ch in target):
        return False
    return "/" in target or "\\" in target or target.lower().endswith(_PATH_SUFFIXES)


@app.command()
def check(
    target: str = typer.Argument(..., help="A file to check, '-' for stdin, or the text itself in quotes."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print the JSON envelope (for agents)."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
    record: Path = typer.Option(None, "--record", help="Also store this answer in REPO's project graph."),
    answer_id: str = typer.Option(None, "--id", help="Id for the recorded answer (default: hash of the text)."),
) -> None:
    """Check every law citation and tax figure in a text. Exit 3 if any rests on repealed law."""
    on = _on(on)
    if target == "-":
        text, label = sys.stdin.read(), "stdin"
    elif Path(target).is_file():
        text, label = Path(target).read_text(encoding="utf-8"), target
    elif _looks_like_path(target):
        err.print(f"[red]No such file: {target}[/red] (to check literal text, include a space)")
        raise typer.Exit(1)
    else:
        text, label = target, "text"
    try:
        result = check_text(text, on, law_pack, log=_log)
        if record is not None:
            from .scan import record_answer
            aid = answer_id or hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
            rec = record_answer(record, aid, text, on, law_pack, log=_log)
            result["recorded"] = {"artifact": rec["artifact"]["id"], "status": rec["verdict"], "store": rec["store"]}
    except StoreLocked as exc:
        raise _locked(exc) from None

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_check(result, label)
        if "recorded" in result:
            r = result["recorded"]
            console.print(f"[dim]Recorded as {r['artifact']} ({r['status']}) in {r['store']}[/dim]")
    if result["verdict"] == "STALE":
        raise typer.Exit(EXIT_STALE)


def _print_check(result: dict, label: str) -> None:
    items = result["items"]
    console.print(f"[bold]{label}[/bold] on {result['on']}: {_v(result['verdict'])}")
    if not items:
        console.print("No law citations or recognised tax figures found.")
        footer()
        return
    table = Table(show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("line", justify="right")
    table.add_column("claim")
    table.add_column("verdict")
    table.add_column("ended")
    table.add_column("now (successor)")
    for n, i in enumerate(items, 1):
        verdict = _v(i["verdict"]) + ("" if i["verified"] else " *")
        succ = i["successor"] or ""
        for n_ in i.get("successorNotes") or []:
            succ += f"\n[yellow]{n_}[/yellow]"
        if not succ and i["verdict"] == "REPEALED":
            succ = "no replacement" + (f" (related: {i['related'][0]['text']})" if i.get("related") else "")
        if succ and i["successorStatus"] and i["successorStatus"] != "IN_FORCE":
            succ += f" ({i['successorStatus']})"
        claim = i["claim"] + "".join(f"\n[yellow]{n_}[/yellow]" for n_ in i.get("ruleNotes") or [])
        table.add_row(str(n), str(i["line"]), claim, verdict, i["endedOn"] or "", succ)
    console.print(table)
    console.print("[bold]Why[/bold]")
    for n, i in enumerate(items, 1):
        if i["path"]:
            console.print(f"  {n}. {' '.join(i['path'])}")
        extra = [x for x in (i["note"], i["source"] and f"source: {i['source']}") if x]
        if extra:
            console.print(f"     [dim]{' | '.join(extra)}[/dim]")
    if result["unverified"]:
        console.print("[yellow]* unverified: not yet checked against the Act's text by a human.[/yellow]")
    footer()


@app.command()
def scan(
    target: Path = typer.Argument(..., help="Repo or folder to scan."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print the JSON envelope (for agents)."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Find code, tests and documents resting on repealed law. Writes <dir>/.inforce/project.rl. Exit 3 if stale."""
    from .scan import scan as run_scan

    on = _on(on)
    if not target.is_dir():
        err.print(f"[red]{target} is not a directory[/red]")
        raise typer.Exit(1)
    try:
        result = run_scan(target, on, law_pack, log=_log)
    except StoreLocked as exc:
        raise _locked(exc) from None
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        _print_scan(result, str(target))
    if result["verdict"] == "STALE":
        raise typer.Exit(EXIT_STALE)


def _short(aid: str) -> str:
    return aid.split("::")[-1] if "::" in aid else aid.rsplit("/", 1)[-1]


def _chain_text(chain: list[dict]) -> str:
    if not chain:
        return ""
    words = {"USED_BY": "used by", "TESTED_BY": "tested by"}
    out = _short(chain[0]["source"])
    for step in chain:
        out += f" →{words.get(step['type'], step['type'])}→ {_short(step['target'])}"
    return out


def _print_scan(result: dict, label: str) -> None:
    arts = result["artifacts"]
    direct = [a for a in arts if a["status"] == "STALE" and not a["via"]]
    inherited = [a for a in arts if a["status"] == "STALE" and a["via"]]
    suspect = [a for a in arts if a["status"] == "SUSPECT"]
    console.print(f"[bold]{label}[/bold] on {result['on']}: {_v(result['verdict'])}  "
                  f"({len(direct)} rest on repealed law, {len(inherited)} use or test them, "
                  f"{len(suspect)} suspect, {len(arts) - len(direct) - len(inherited) - len(suspect)} current)")
    if direct:
        t = Table(title="STALE: encodes or cites repealed law", title_justify="left")
        for col in ("artifact", "line", "rests on", "ended", "now (successor)"):
            t.add_column(col)
        for a in direct:
            for n, b in enumerate(sorted(a["because"], key=lambda b: (b["line"] or 0, b["target"]))):
                now = (b["successor"] or "") + "".join(f"\n[yellow]{n_}[/yellow]" for n_ in b.get("successorNotes") or [])
                t.add_row(a["id"] if n == 0 else "", str(b["line"] or ""), b["rule"] or b["target"],
                          b["endedOn"] or "", now)
        console.print(t)
    if inherited:
        t = Table(title="ALSO CHECK: uses or tests the above", title_justify="left")
        t.add_column("artifact")
        t.add_column("why")
        for a in inherited:
            t.add_row(a["id"], _chain_text(a["chain"]) or ", ".join(a["via"]))
        console.print(t)
    if suspect:
        console.print("[yellow]SUSPECT[/yellow] (rests on unverified or unrecognised law): "
                      + ", ".join(a["id"] for a in suspect))
    if any(a["status"] == "STALE" for a in arts):
        console.print("[yellow]Rules shown are not yet verified against the Act's text.[/yellow]")
    for w in result.get("warnings", []):
        console.print(f"[yellow]warning[/yellow] {w}")
    console.print(f"[dim]Project graph: {result['store']}[/dim]")
    footer()


@app.command()
def brief(
    target: str = typer.Argument(..., help="A file (in a repo: rescans it first), or a question / draft answer."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print JSON (for agents)."),
    repo: Path = typer.Option(None, "--repo", help="Repo root (default: nearest folder with .inforce/ or .git/)."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """One screen: VERDICT, TRUTH, WHY, WHAT RESTS ON IT, RE-CHECK LIST. Exit 3 if stale."""
    from .brief import brief as run_brief

    on = _on(on)
    try:
        b = run_brief(target, on, law_pack, repo=repo, log=_log)
    except StoreLocked as exc:
        raise _locked(exc) from None
    if as_json:
        print(json.dumps(b, indent=2, ensure_ascii=False, default=str))
    else:
        _print_brief(b)
    if b["verdict"] == "STALE":
        raise typer.Exit(EXIT_STALE)


def _print_brief(b: dict) -> None:
    star = " *" if b["unverified"] else ""
    console.print(f"[bold]VERDICT[/bold]  {b['target']} on {b['on']}: {_v(b['verdict'])}")
    console.print("\n[bold]TRUTH[/bold]  what the law says now")
    if not b["truth"]:
        console.print("  No repealed law found." if b["verdict"] != "STALE" else "")
    for t in b["truth"]:
        if t.get("was"):
            if t.get("scale"):
                where = t["now"].split(" (whole scale)")[0]
                console.print(f"  - {t['was']}: [red]ended {t['endedOn']}[/red]. Replaced as a whole by "
                              f"{where} [dim]({t['nowRef']})[/dim]:{star}")
                for r in t["scale"]:
                    console.print(f"      {r['text']} [dim]({r['id']})[/dim]")
            elif t["now"]:
                console.print(f"  - {t['was']}: [red]ended {t['endedOn']}[/red]. Now: {t['now']} "
                              f"[dim]({t['nowRef']})[/dim]{star}")
            else:
                console.print(f"  - {t['was']}: [red]ended {t['endedOn']}[/red], with no replacement.{star}")
            for x in t.get("related") or []:
                console.print(f"      related, not a successor: {x['text']} [dim]({x['id']})[/dim]")
            for n_ in t.get("nowNotes") or []:
                console.print(f"      [yellow]{n_}[/yellow]")
        else:
            console.print(f"  - {t['now']}: [green]{t.get('status', 'IN_FORCE')}[/green]{star}")
            for n_ in t.get("nowNotes") or []:
                console.print(f"      [yellow]{n_}[/yellow]")
    console.print("\n[bold]WHY[/bold]")
    for w in b["why"]:
        if w.get("chain"):
            console.print(f"  - {_short(w['artifact'])}: {_chain_text(w['chain'])}")
        elif w.get("path"):
            head = _short(w["artifact"]) if w.get("artifact") else w.get("claim")
            console.print(f"  - {head} (line {w.get('line')}): {' '.join(w['path'])}")
    console.print("\n[bold]WHAT RESTS ON IT[/bold]")
    if not b["rests_on_it"]:
        console.print("  Nothing else in the project graph." if b["repo"] else
                      "  Not in a scanned repo; run `inforce scan` to see what rests on it.")
    for r in b["rests_on_it"]:
        console.print(f"  - {r['where']}  {_short(r['artifact'])} ({r['kind']})")
    console.print("\n[bold]RE-CHECK LIST[/bold]")
    if not b["recheck"]:
        console.print("  Nothing to re-check.")
    for n, r in enumerate(b["recheck"], 1):
        console.print(f"  {n}. {r['where']}  {_short(r['artifact'])}: {r['action']}")
        for x in r.get("replace", []):
            if x.get("was"):
                console.print(f"       {x['was']}  ->  {x['now'] or 'ended with no replacement: remove it'}")
                for rel in x.get("related") or []:
                    console.print(f"         related, not a successor: {rel['text']} ({rel['id']})")
    if b["unverified"]:
        console.print("\n[yellow]* the law pack's rules are not yet verified against the Act's text.[/yellow]")
    footer()


@app.command()
def serve(
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Run the MCP server on stdio (tools: inforce_check, inforce_scan, inforce_brief)."""
    from .server import build_server

    build_server(law_pack).run("stdio")


@app.command()
def fallout(
    instrument: str = typer.Argument(..., help="Repealed Act: akn or short name (e.g. IDITRA)."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """What fell and what was saved when an Act was repealed."""
    on = _on(on)
    try:
        with open_store(law_pack, read_only=True, log=_log) as store:
            inst = law.instrument_status(store, instrument, on)
            rows = law.fallout(store, instrument, on) if inst else []
    except StoreLocked as exc:
        raise _locked(exc) from None
    if inst is None:
        err.print(f"[red]No Act {instrument!r} in the law pack.[/red]")
        raise typer.Exit(1)

    for r in rows:
        for k in ("repealedOn", "savedUntil"):
            if isinstance(r.get(k), dt.date):
                r[k] = r[k].isoformat()
    if as_json:
        print(json.dumps({"instrument": inst["akn"], "status": inst["status"], "on": on, "items": rows,
                          "disclaimer": DISCLAIMER}, indent=2, ensure_ascii=False))
        return
    console.print(f"[bold]{inst['title'] or inst['akn']}[/bold] on {on}: {_v(inst['status'])}"
                  + (f" (repealed {inst['endedOn']} by {inst['repealedByTitle'] or inst['repealedBy']})"
                     if inst["repealedBy"] else ""))
    if not rows:
        console.print("No dependents (grants or subsidiary instruments) recorded for this Act.")
    else:
        table = Table()
        for col in ("dependent", "rests on", "verdict", "saved by", "until"):
            table.add_column(col)
        for r in rows:
            table.add_row(r["dependent"], r["restsOn"], _v(r["verdict"]), r["savedBy"] or "",
                          r["savedUntil"] or ("" if not r["savedBy"] else "no end date"))
        console.print(table)
    footer()


@app.command()
def keystones(
    target: Path = typer.Argument(..., help="Repo with a project graph (.inforce/project.rl)."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Rules the repo rests on most: artifacts that encode or cite each one, plus what uses or tests those."""
    from .scan import project_store_path

    on = _on(on)
    ps = project_store_path(target)
    if not ps.exists():
        err.print(f"[red]{ps} not found; run `inforce scan {target}` first[/red]")
        raise typer.Exit(1)
    try:
        with open_store(ps, read_only=True, log=_log) as store:
            rows = law.keystones(store, on)
    except StoreLocked as exc:
        raise _locked(exc) from None
    if as_json:
        print(json.dumps({"on": on, "items": rows, "disclaimer": DISCLAIMER}, indent=2, ensure_ascii=False, default=str))
        return
    _print_keystones(rows, str(target), on)


def _print_keystones(rows: list[dict], label: str, on: str) -> None:
    t = Table(title=f"Keystones: the rules {label} rests on most (on {on})", title_justify="left")
    for col in ("#", "rule", "status", "direct", "downstream", "weight", "for example"):
        t.add_column(col, justify="right" if col in ("#", "direct", "downstream", "weight") else "left")
    for n, r in enumerate(rows, 1):
        examples = ", ".join(_short(x) for x in r["directArtifacts"][:3])
        t.add_row(str(n), f"{r['text']}\n[dim]{r['rule']}[/dim]", _v(r["status"]) + ("" if r["verified"] else " *"),
                  str(r["direct"]), str(r["downstream"]), str(r["weight"]), examples)
    console.print(t if rows else "No rules linked yet: run `inforce scan` first.")
    console.print("[dim]direct = encodes or cites the rule; downstream = uses or tests those, up to 3 hops. "
                  "* unverified[/dim]")
    footer()


@app.command()
def ask(
    question: str = typer.Argument(..., help="A question about Nigerian tax rules."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    top: int = typer.Option(5, "--top", help="How many rules to show."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Which rules answer QUESTION, and are they in force on the date? (Retrieval only: no generated answer.)"""
    from .ask import ask as run_ask

    on = _on(on)
    try:
        r = run_ask(question, on, law_pack, top=top, log=_log)
    except StoreLocked as exc:
        raise _locked(exc) from None
    if as_json:
        print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
        return
    _print_ask(r)


def _print_ask(r: dict) -> None:
    mode = "vector + full-text" if r["mode"] == "hybrid" else "full-text only (embedding model not available)"
    console.print(f"[bold]{r['question']}[/bold]  on {r['on']}  [dim]({mode})[/dim]")
    a = r["answer"]
    if a is None:
        console.print("No matching rule in the law pack. InForce cannot answer this; say so rather than guess.")
        footer()
        return
    if a["ref"] and a["how"] == "in force":
        console.print(f"\n[bold]Rule on {r['on']}:[/bold] {a['text']} [dim]({a['ref']}, in force)[/dim]")
    elif a["ref"]:
        console.print(f"\n[bold]Rule on {r['on']}:[/bold] {a['how'].replace('; replaced by', '')}. "
                      f"Replaced by: {a['text']} [dim]({a['ref']})[/dim]")
    else:
        console.print(f"\n[bold]Rule on {r['on']}:[/bold] [red]{a['how']}[/red]")
    t = Table(title="Matching rules", title_justify="left")
    for col in ("#", "rule", "status", "now (successor)", "found by"):
        t.add_column(col)
    for n, i in enumerate(r["items"], 1):
        succ = i["successor"] or ("no replacement" if i["status"] == "REPEALED" else "")
        for x in i["related"]:
            succ += f"\n[dim]related, not a successor: {x['text']}[/dim]"
        for n_ in i.get("successorNotes") or []:
            succ += f"\n[yellow]{n_}[/yellow]"
        rule_cell = f"{i['text']}\n[dim]{i['rule']}[/dim]" + "".join(f"\n[yellow]{n_}[/yellow]" for n_ in i.get("notes") or [])
        t.add_row(str(n), rule_cell, _v(i["status"]) + ("" if i["verified"] else " *"),
                  succ, ", ".join(i["via"]))
    console.print(t)
    console.print("[dim]* unverified. InForce retrieves rules and their status; it does not write answers.[/dim]")
    footer()


@app.command()
def diff(
    known_on: list[str] = typer.Option(..., "--known-on", help="Two dates (YYYY-MM-DD): --known-on D1 --known-on D2."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """What was on record on D1 versus D2: which published version of each Act (e.g. gazetted vs certified)."""
    if len(known_on) != 2:
        err.print("[red]Give exactly two dates: --known-on D1 --known-on D2[/red]")
        raise typer.Exit(1)
    d1, d2 = _on(known_on[0]), _on(known_on[1])
    try:
        with open_store(law_pack, read_only=True, log=_log) as store:
            r = law.diff_known_on(store, d1, d2)
    except StoreLocked as exc:
        raise _locked(exc) from None
    if as_json:
        print(json.dumps({**r, "disclaimer": DISCLAIMER}, indent=2, ensure_ascii=False, default=str))
        return
    _print_diff(r)


def _sec(n: str) -> str:
    """'s.182(2)' for a section number, the text itself for e.g. 'long title (Commencement)'."""
    return f"s.{n}" if n[:1].isdigit() else n


def _print_diff(r: dict) -> None:
    d1, d2 = r["d1"], r["d2"]
    t = Table(title=f"Versions on record: {d1} vs {d2}", title_justify="left")
    for col in ("Act", f"on {d1}", f"on {d2}", "changed"):
        t.add_column(col)

    def cell(vs: list[dict]) -> str:
        if not vs:
            return "[dim]none on record[/dim]"
        return ", ".join(f"{x['version']} (recorded {x['recordedAt'] or '[yellow]date unknown[/yellow]'})"
                         + ("" if x["verified"] else " *") for x in vs)
    for a in r["acts"]:
        t.add_row(a["short"] or a["akn"], cell(a["d1"]), cell(a["d2"]), "[bold]yes[/bold]" if a["changed"] else "no")
    console.print(t if r["acts"] else "No Act versions are recorded in the law pack.")
    if r["provisions"]:
        for p in r["provisions"]:
            console.print(f"  {p['akn']}: on record {d1}: {p['d1']}, {d2}: {p['d2']}  [dim]{p['summary'] or ''}[/dim]")
    else:
        console.print(f"[dim]Provision level: {r['provisionsWithRecordDates']} provisions carry record dates; "
                      "none differs between these dates. Text-level differences between versions are not "
                      "recorded in the law pack yet.[/dim]")
    if r.get("numbering"):
        t = Table(title="Section numbers that differ between the editions", title_justify="left")
        for col in ("provision", f"on {d1}", f"on {d2}"):
            t.add_column(col)

        def num(x: dict) -> str:
            return f"{_sec(x['number'])} ({x['version']}" + (f", p. {x['page']}" if x.get("page") else "") + ")"
        for n in r["numbering"]:
            label = f"{n['act']} {n['summary'] or n['akn']}\n[dim]{n['akn']}[/dim]"
            if n.get("note"):
                label += f"\n[yellow]{n['note']}[/yellow]"
            t.add_row(label, num(n["d1"]), num(n["d2"]))
        console.print(t)
    if r.get("numberingUnchecked"):
        console.print(f"[dim]{len(r['numberingUnchecked'])} provision(s) are numbered in only one of these editions "
                      "(not yet checked in the other): " + ", ".join(r["numberingUnchecked"]) + "[/dim]")
    console.print("[dim]* unverified[/dim]")
    footer()


@app.command()
def verify(
    unverified_only: bool = typer.Option(False, "--unverified", help="Only list entries not yet verified."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    summary: bool = typer.Option(False, "--summary", help="Print only the one-line verification status."),
    update_docs: list[Path] = typer.Option(None, "--update-docs",
                                           help="Rewrite the verify-status block in these files (repeatable)."),
    sheet: Path = typer.Option(None, "--sheet", help="Write the checkbox sheet (e.g. docs/VERIFY.md); keeps ticks."),
    apply: Path = typer.Option(None, "--apply", help="Set verified: true for the rows ticked in this sheet."),
    dry_run: bool = typer.Option(False, "--dry-run", help="With --apply: show the diff, change nothing."),
    rules: Path = typer.Option(RULES_DIR, help="Directory of rule YAML files."),
) -> None:
    """Every law entry with its source and verified flag: the checklist for checking against the Act's text."""
    from . import verify_sheet as vs

    if sheet:
        n = vs.write_sheet(rules, sheet)
        console.print(f"Wrote {sheet}: {n} rows, grouped by Act and section. Tick rows, then run "
                      f"`inforce verify --apply {sheet}`.")
        return
    if apply:
        try:
            r = vs.apply_ticks(apply, rules, dry_run=dry_run)
        except RuntimeError as exc:
            err.print(f"[red]Not applied; the YAML is unchanged: {exc}[/red]")
            raise typer.Exit(1) from None
        if r.diff:
            console.print(r.diff, markup=False, highlight=False)
        console.print(f"{'Would set' if dry_run else 'Set'} verified: true on {len(r.applied)} entries"
                      + (f"; {len(r.already)} ticked rows were already verified" if r.already else "")
                      + ("." if not dry_run else " (dry run: nothing written)."))
        for u in r.unknown:
            console.print(f"[yellow]ticked row not found in the YAML (left alone): {u}[/yellow]")
        if r.applied and not dry_run:
            console.print("Next: `inforce load --allow-unverified --force`, `inforce export`, and "
                          "`inforce verify --update-docs README.md --update-docs docs/DEVPOST.md`.")
        return
    if summary or update_docs:
        line = loader.verify_summary(rules)
        for f in update_docs or []:
            f.write_text(loader.update_status_block(f.read_text(encoding="utf-8"), line), encoding="utf-8")
            console.print(f"[dim]updated {f}[/dim]")
        print(line)
        return
    items = loader.verify_list(rules)
    shown = [i for i in items if not (unverified_only and i["verified"])]
    n_ok = sum(i["verified"] for i in items)
    if as_json:
        print(json.dumps({"verified": n_ok, "total": len(items), "items": shown}, indent=2, ensure_ascii=False))
        return
    t = Table(title=f"Law entries: {n_ok} of {len(items)} verified", title_justify="left", show_lines=False)
    for col in ("kind", "entry", "says", "source", "verified", "where"):
        t.add_column(col, overflow="fold")
    for i in shown:
        t.add_row(i["kind"], i["entry"], i["what"],
                  (i["source"] + (f", p. {i['page']}" if i.get("page") else "")) if i["source"] else "[red]no source[/red]",
                  "[green]yes[/green]" if i["verified"] else "[yellow]no[/yellow]", i["where"])
    console.print(t)
    console.print("[dim]To verify an entry: check it against the Act's text, then set `verified: true` on it in "
                  "the YAML yourself. InForce never sets it.[/dim]")
    footer()


@app.command()
def export(
    out: Path = typer.Option(Path("web/export.json"), "--out", help="Where to write the JSON for the browser page."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Write web/export.json for the static browser checker (statuses computed by Cypher at each change date)."""
    from .export import write_export

    try:
        data = write_export(law_pack, out)
    except StoreLocked as exc:
        raise _locked(exc) from None
    console.print(f"Wrote {out}: {len(data['rules'])} rules, {len(data['acts'])} Acts, "
                  f"{len(data['provisions'])} numbered provisions, change dates {', '.join(data['dates'][1:])}")
    footer()


whatif_app = typer.Typer(help="Hypothetical changes, measured then rolled back.", no_args_is_help=True)
app.add_typer(whatif_app, name="whatif")


@whatif_app.command("repeal")
def whatif_repeal_cmd(
    target: str = typer.Argument(..., help="Provision akn, Act akn or Act short name (e.g. IDITRA)."),
    on: str = typer.Option(None, "--on", help="Date of the hypothetical repeal (and of the check). Default: today."),
    repo: Path = typer.Option(None, "--repo", help="Also show which artifacts in REPO would turn STALE."),
    in_place: bool = typer.Option(False, "--in-place",
                                  help="Run on the stores themselves, not temp copies (content is restored by "
                                       "rollback, but the .rl files are rewritten)."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """What would fall if TARGET were repealed? Measured inside a transaction, then rolled back."""
    from .whatif import whatif_repeal

    on = _on(on)
    try:
        r = whatif_repeal(target, on, law_pack, repo=repo, in_place=in_place)
    except StoreLocked as exc:
        raise _locked(exc) from None
    except FileNotFoundError as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from None
    if not r["law"]["found"]:
        err.print(f"[red]{target!r} is not a provision or Act in the law pack.[/red]")
        raise typer.Exit(1)
    if as_json:
        print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
        return
    _print_whatif(r)


def _print_whatif(r: dict) -> None:
    console.print(f"[bold]What if {r['target']} were repealed on {r['on']}?[/bold]  "
                  f"({'in place' if r['inPlace'] else 'on temporary copies'}; rolled back afterwards)")
    sections = [("Law", r["law"])] + ([("Repo " + r["repo"]["path"], r["repo"])] if r["repo"] else [])
    for title, sec in sections:
        if not sec["changes"]:
            console.print(f"\n{title}: no status changes"
                          + ("" if sec["found"] else " (it does not rest on this provision or Act)"))
            continue
        t = Table(title=f"{title}: what changes", title_justify="left")
        for col in ("kind", "id", "", "before", "after"):
            t.add_column(col)
        for c in sec["changes"]:
            t.add_row(c["kind"], c["id"], c["label"], _v(c["before"]), _v(c["after"]))
        console.print(t)
    t = Table(title="Rollback check", title_justify="left")
    for col in ("store", "before", "during", "after", "restored"):
        t.add_column(col)
    for title, sec in sections:
        c = sec["counts"]
        cell = lambda x: f"{x['nodes']} nodes, {x['rels']} rels, {x['sha256']}"  # noqa: E731
        t.add_row(title, cell(c["before"]), cell(c["during"]), cell(c["after"]),
                  "[green]yes[/green]" if sec["unchanged"] else "[red]NO[/red]")
    console.print(t)
    footer()


@app.command()
def demo(
    fast: bool = typer.Option(False, "--fast", help="No pauses between steps (CI)."),
    on: str = typer.Option("2026-11-25", "--on", help="Date the demo checks against (fixed, so output is stable)."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Run the whole story offline: stale answer, stale repo, brief, the recorded agent fix, zero STALE.

    Works on a temporary copy of demo/naira-payroll, so the committed demo stays as it is.
    Exits 1 if any step does not show what it should.
    """
    from . import demo as d
    from .brief import brief as run_brief
    from .scan import scan as run_scan

    on = _on(on)
    results: list[tuple[str, bool, str]] = []
    counter = [0]

    def step(title: str, why: str) -> None:
        counter[0] += 1
        n = counter[0]
        if not fast and n > 1:
            console.input("\n[dim]Press Enter for the next step...[/dim]")
        console.rule(f"[bold]{n}. {title}[/bold]")
        console.print(f"[dim]{why}[/dim]\n")

    def expect(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))
        mark = "[green]as expected[/green]" if ok else "[bold red]NOT as expected[/bold red]"
        console.print(f"\n{mark}: {detail}")

    try:
        repo = d.copy_demo()
        step("The law pack", f"{law_pack}: Nigeria's tax reform as a graph in Relate (single-file store).")
        with open_store(law_pack, read_only=True, log=_log) as store:
            counts = {r["label"]: r["n"] for r in store.run("law_counts")}
        console.print(", ".join(f"{k} {v}" for k, v in counts.items()))
        console.print("[yellow]All rules are unverified until checked against the Act's text by a human.[/yellow]")
        expect("law pack", counts.get("Rule", 0) > 0, f"{counts.get('Rule', 0)} rules loaded")

        answer = repo / "answers" / "stale_answer.md"
        step("An AI answer written in 2025", f"inforce check {answer.relative_to(repo.parent)}")
        r = check_text(answer.read_text(encoding="utf-8"), on, law_pack, log=_log)
        _print_check(r, "answers/stale_answer.md")
        expect("stale answer", r["verdict"] == "STALE",
               f"verdict {r['verdict']}, {sum(i['verdict'] == 'REPEALED' for i in r['items'])} claims rest on repealed law")

        step("The codebase", "inforce scan: code constants, functions, tests, docs and templates, linked to the law.")
        rep = run_scan(repo, on, law_pack, log=_log)
        _print_scan(rep, "demo/naira-payroll (copy)")
        n_stale = sum(a["status"] == "STALE" for a in rep["artifacts"])
        expect("stale repo", n_stale > 0, f"{n_stale} STALE artifacts")

        step("Which rules does it rest on most?", "inforce keystones: direct plus downstream artifacts per rule.")
        with open_store(repo / ".inforce" / "project.rl", read_only=True, log=_log) as store:
            ks = law.keystones(store, on)
        _print_keystones(ks, "demo/naira-payroll (copy)", on)
        expect("keystones", bool(ks) and ks[0]["status"] == "REPEALED",
               f"top keystone: {ks[0]['rule']} ({ks[0]['weight']} artifacts)" if ks else "none")

        step("Before editing paye.py", "inforce brief: what an agent sees before it touches the file.")
        b = run_brief(str(repo / "payroll" / "paye.py"), on, law_pack, repo=repo, log=_log)
        _print_brief(b)
        expect("brief", b["verdict"] == "STALE" and bool(b["recheck"]), f"{len(b['recheck'])} items to re-check")

        step("The agent's fix, replayed", f"Edits from the recorded Claude Code session ({d.AGENT_LOG.name}), "
             "applied to the copy, then a rescan. No model is called.")
        rp = d.replay_agent_fix(repo)
        console.print(f"Replayed {rp.edits} edits to {len(rp.files)} files: {', '.join(rp.files)}")
        if rp.skipped:
            console.print(f"[yellow]Edits that no longer apply: {', '.join(rp.skipped)}[/yellow]")
        rep2 = run_scan(repo, on, law_pack, log=_log)
        _print_scan(rep2, "demo/naira-payroll (copy, after the fix)")
        n_after = sum(a["status"] == "STALE" for a in rep2["artifacts"])
        expect("fixed repo", n_after == 0 and not rp.skipped, f"{n_stale} STALE before, {n_after} after")

        step("The rewritten answer", "inforce check on the answer the agent rewrote.")
        r2 = check_text(answer.read_text(encoding="utf-8"), on, law_pack, log=_log)
        _print_check(r2, "answers/stale_answer.md (rewritten)")
        expect("fixed answer", r2["verdict"] != "STALE", f"verdict {r2['verdict']}")

        step("Ask the law pack", 'inforce ask "Can I still claim the consolidated relief allowance?"')
        from .ask import ask as run_ask
        qa = run_ask("Can I still claim the consolidated relief allowance?", on, law_pack, log=_log)
        _print_ask(qa)
        expect("ask", bool(qa["items"]) and qa["items"][0]["rule"] == "ng.pit.cra.old"
               and qa["items"][0]["status"] == "REPEALED",
               f"top rule {qa['items'][0]['rule'] if qa['items'] else '-'} ({qa['mode']})")

        from .whatif import whatif_repeal
        step("What if the new PAYE scale were repealed?",
             "inforce whatif repeal akn/ng/act/2025/7/sec_58 --repo <fixed copy>: measured in a transaction, "
             "then rolled back.")
        w = whatif_repeal("akn/ng/act/2025/7/sec_58", on, law_pack, repo=repo)
        _print_whatif(w)
        newly = [c for c in w["repo"]["changes"] if c["after"] == "STALE"]
        expect("what-if (repo)", bool(newly) and w["law"]["unchanged"] and w["repo"]["unchanged"],
               f"{len(newly)} artifacts would turn STALE; both stores restored")

        step("What if the savings clause went?",
             "inforce whatif repeal akn/ng/act/2025/7/sec_182_2: existing pioneer certificates rest on it.")
        w2 = whatif_repeal("akn/ng/act/2025/7/sec_182_2", on, law_pack)
        _print_whatif(w2)
        fell = [c for c in w2["law"]["changes"] if c["after"] == "FELL"]
        expect("what-if (law)", bool(fell) and w2["law"]["unchanged"], f"{len(fell)} grant(s) would fall")

        step("Two official editions, two numberings",
             "inforce diff --known-on 2025-12-31 --known-on 2026-01-07: the gazetted text (26 Jun 2025) and the "
             "certified copy (Jan 2026) number some sections differently.")
        with open_store(law_pack, read_only=True, log=_log) as store:
            dd = law.diff_known_on(store, "2025-12-31", "2026-01-07")
        _print_diff(dd)
        moves = {(n["d1"]["number"], n["d2"]["number"]) for n in dd["numbering"]}
        expect("diff", {("183(2)", "182(2)"), ("196", "195")} <= moves,
               ", ".join(f"{_sec(a)} -> {_sec(b)}" for a, b in sorted(moves)))
    except StoreLocked as exc:
        raise _locked(exc) from None

    console.rule("[bold]Summary[/bold]")
    for name, ok, detail in results:
        console.print(f"  {'[green]PASS[/green]' if ok else '[red]FAIL[/red]'}  {name}: {detail}")
    console.print(f"[dim]Demo copy: {repo}[/dim]")
    footer()
    if not all(ok for _, ok, _ in results):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
