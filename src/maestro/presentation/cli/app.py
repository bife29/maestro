"""`maestro` command-line entry point."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from maestro import __version__
from maestro.infrastructure.config import load_settings

ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Config file (TOML).")]

app = typer.Typer(
    name="maestro",
    help="AI-native engineering management toolkit — MCP · RAG · agents · DORA.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.command()
def version() -> None:
    """Show the installed version."""
    console.print(f"maestro [bold]{__version__}[/bold]")


@app.command()
def doctor(config: ConfigOption = Path("maestro.toml")) -> None:
    """Check local setup: Python, config file, providers and data directories."""
    settings = load_settings(config)
    table = Table(title="maestro doctor", show_lines=False)
    table.add_column("Check", style="cyan")
    table.add_column("Value")
    table.add_column("Status", justify="center")

    table.add_row("python", f"{platform.python_version()} ({sys.executable})", "✅")
    table.add_row("config", str(config), "✅" if config.exists() else "⚠️ defaults")
    table.add_row("devops.provider", settings.devops.provider, "✅")
    table.add_row("llm.provider", settings.llm.provider, "✅")
    table.add_row(
        "data_dir",
        str(settings.devops.data_dir),
        "✅" if settings.devops.data_dir.exists() else "⚠️ run `maestro seed`",
    )
    table.add_row(
        "audit.dir",
        str(settings.audit.dir),
        "✅" if settings.audit.dir.exists() else "— created on first write",
    )
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
