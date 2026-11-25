"""InForce command line. Built with Relate."""
from __future__ import annotations

import datetime as dt
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
    err.print(f"[yellow]{msg}[/yellow]")


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
) -> None:
    """Build the law pack .rl from the rule YAML files."""
    try:
        report = loader.load(rules, out, allow_unverified=allow_unverified, log=_log)
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


@app.command()
def check(
    target: str = typer.Argument(..., help="A file to check, '-' for stdin, or the text itself in quotes."),
    on: str = typer.Option(None, "--on", help=ON_HELP),
    as_json: bool = typer.Option(False, "--json", help="Print the JSON envelope (for agents)."),
    law_pack: Path = typer.Option(LAW_PACK, "--law", help=LAW_HELP),
) -> None:
    """Check every law citation and tax figure in a text. Exit 3 if any rests on repealed law."""
    on = _on(on)
    if target == "-":
        text, label = sys.stdin.read(), "stdin"
    elif Path(target).is_file():
        text, label = Path(target).read_text(encoding="utf-8"), target
    else:
        text, label = target, "text"
    try:
        result = check_text(text, on, law_pack, log=_log)
    except StoreLocked as exc:
        raise _locked(exc) from None

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_check(result, label)
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
        if succ and i["successorStatus"] and i["successorStatus"] != "IN_FORCE":
            succ += f" ({i['successorStatus']})"
        table.add_row(str(n), str(i["line"]), i["claim"], verdict, i["endedOn"] or "", succ)
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


if __name__ == "__main__":
    app()
