"""InForce command line. Built with Relate."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import loader
from .store import StoreLocked

DISCLAIMER = "InForce checks whether a provision is in force. It is not legal or tax advice."
DEFAULT_RULES = Path("data/rules")
DEFAULT_LAW = Path("data/ng-tax-2026.rl")

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Find answers, code and documents that still run on repealed law. Built with Relate.")
console = Console()
err = Console(stderr=True)


@app.callback()
def main() -> None:
    """Keeps Typer in multi-command mode while only `load` exists."""


def footer() -> None:
    console.print(f"\n[dim]{DISCLAIMER}[/dim]")


@app.command()
def load(
    allow_unverified: bool = typer.Option(False, "--allow-unverified",
                                          help="Load law entries a human has not yet verified."),
    rules: Path = typer.Option(DEFAULT_RULES, help="Directory of rule YAML files."),
    out: Path = typer.Option(DEFAULT_LAW, help="Law pack .rl file to (re)build."),
) -> None:
    """Build the law pack .rl from the rule YAML files."""
    try:
        report = loader.load(rules, out, allow_unverified=allow_unverified,
                             log=lambda m: err.print(f"[yellow]{m}[/yellow]"))
    except loader.UnverifiedLaw as exc:
        err.print(f"[red]Refusing to load: {exc}[/red]")
        for e in exc.entries[:15]:
            err.print(f"  - {e}")
        if len(exc.entries) > 15:
            err.print(f"  ... and {len(exc.entries) - 15} more (see `inforce verify`)")
        raise typer.Exit(1)
    except loader.BadReference as exc:
        err.print(f"[red]Bad reference in rule YAML: {exc}[/red]")
        raise typer.Exit(1)
    except StoreLocked as exc:
        err.print(f"[red]{exc}[/red]")
        raise typer.Exit(StoreLocked.exit_code)

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


if __name__ == "__main__":
    app()
