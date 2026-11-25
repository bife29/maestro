"""`maestro` command-line entry point."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from maestro import __version__
from maestro.application.charts import RenderCharts
from maestro.application.metrics import ComputeDora, ComputePrFlow
from maestro.application.seed import GenerateSeed
from maestro.domain.metrics import DoraLevel
from maestro.infrastructure.charts.matplotlib_png import MatplotlibChartRenderer
from maestro.infrastructure.config import Settings, load_settings
from maestro.infrastructure.devops.local_json import LocalJsonDatasetWriter, LocalJsonProvider

ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Config file (TOML).")]
MonthsOption = Annotated[
    int, typer.Option("--months", "-m", min=1, max=36, help="Analysis window in 30-day months.")
]
RepoOption = Annotated[str | None, typer.Option("--repo", "-r", help="Filter by repository id or name.")]
JsonFlag = Annotated[bool, typer.Option("--json", help="Print JSON instead of a table.")]

# Fixed reference date so `seed` and `metrics` agree without arguments (dataset ends here).
DATASET_END = datetime(2026, 12, 1, tzinfo=UTC)
LEVEL_STYLE = {
    DoraLevel.ELITE: "bold green",
    DoraLevel.HIGH: "green",
    DoraLevel.MEDIUM: "yellow",
    DoraLevel.LOW: "red",
}

app = typer.Typer(
    name="maestro",
    help="AI-native engineering management toolkit — MCP · RAG · agents · DORA.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
metrics_app = typer.Typer(help="DORA and pull-request flow metrics.", no_args_is_help=True)
app.add_typer(metrics_app, name="metrics")
console = Console()


def _provider(settings: Settings) -> LocalJsonProvider:
    return LocalJsonProvider(settings.devops.data_dir)


def _fmt(value: float | None, suffix: str = "", digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}{suffix}"


def _level(level: DoraLevel) -> str:
    return f"[{LEVEL_STYLE[level]}]{level.value}[/]"


@app.command()
def seed(
    config: ConfigOption = Path("maestro.toml"),
    seed_value: Annotated[
        int | None, typer.Option("--seed", help="Random seed (default from config).")
    ] = None,
    months: Annotated[
        int | None, typer.Option("--months", "-m", help="Months of history (default from config).")
    ] = None,
) -> None:
    """Generate the deterministic synthetic dataset (repositories, PRs, deployments, incidents)."""
    settings = load_settings(config)
    dataset = GenerateSeed(
        seed=seed_value if seed_value is not None else settings.seed.default,
        months=months or settings.seed.months,
        end=DATASET_END,
    ).execute()
    out = LocalJsonDatasetWriter(settings.devops.data_dir).write(dataset)
    console.print(
        f"[green]✓[/] dataset written to [bold]{out}[/]: {len(dataset.repositories)} repositories · "
        f"{len(dataset.pull_requests)} PRs · {len(dataset.commits)} commits · "
        f"{len(dataset.deployments)} deployments · {len(dataset.incidents)} incidents"
    )


@metrics_app.command("dora")
def metrics_dora(
    config: ConfigOption = Path("maestro.toml"),
    months: MonthsOption = 12,
    repo: RepoOption = None,
    as_json: JsonFlag = False,
) -> None:
    """Deployment frequency, lead time, change failure rate and MTTR per repository (DORA)."""
    results = ComputeDora(_provider(load_settings(config))).execute(DATASET_END, months, repo)
    if as_json:
        payload = [
            {
                "repository": r.repository.name,
                **_dora_dict(r.overall),
                "overall_level": r.overall.overall_level.value,
            }
            for r in results
        ]
        console.print_json(json.dumps(payload))
        return
    table = Table(title=f"DORA metrics — last {months} months (ending {DATASET_END:%d/%m/%Y})")
    for col in ("Repository", "Deploys/wk", "Lead time p50", "CFR", "MTTR p50", "Overall"):
        table.add_column(col, justify="right" if col != "Repository" else "left")
    for r in results:
        m = r.overall
        table.add_row(
            r.repository.name,
            f"{_fmt(m.deployment_frequency_per_week)} {_level(m.frequency_level)}",
            f"{_fmt(m.lead_time_hours_p50, 'h')} {_level(m.lead_time_level)}",
            f"{m.change_failure_rate:.0%} {_level(m.cfr_level)}",
            f"{_fmt(m.mttr_hours_p50, 'h')} {_level(m.mttr_level)}",
            _level(m.overall_level),
        )
    console.print(table)
    console.print(
        "[dim]Overall = worst of the four metrics (a team is as fast as its slowest capability).[/]"
    )


def _dora_dict(m: object) -> dict[str, object]:
    d: dict[str, object] = dict(asdict(m))  # type: ignore[call-overload]
    d.pop("period", None)
    return d


@metrics_app.command("pr-flow")
def metrics_pr_flow(
    config: ConfigOption = Path("maestro.toml"),
    months: MonthsOption = 12,
    repo: RepoOption = None,
    as_json: JsonFlag = False,
) -> None:
    """Pull-request flow: review latency, cycle time, size, rework and AI-review coverage."""
    results = ComputePrFlow(_provider(load_settings(config))).execute(DATASET_END, months, repo)
    if as_json:
        console.print_json(
            json.dumps([{"repository": r.repository.name, **_dora_dict(r.metrics)} for r in results])
        )
        return
    table = Table(title=f"Pull-request flow — last {months} months")
    for col in (
        "Repository",
        "Opened",
        "Merged",
        "1st review p50",
        "Cycle p50",
        "Size (lines)",
        "Rework",
        "AI-reviewed",
    ):
        table.add_column(col, justify="right" if col != "Repository" else "left")
    for r in results:
        m = r.metrics
        table.add_row(
            r.repository.name,
            str(m.opened),
            str(m.merged),
            _fmt(m.time_to_first_review_hours_p50, "h"),
            _fmt(m.cycle_time_hours_p50, "h"),
            _fmt(m.size_lines_mean, "", 0),
            f"{m.rework_rate:.0%}",
            f"{m.ai_reviewed_rate:.0%}",
        )
    console.print(table)


@app.command()
def charts(
    config: ConfigOption = Path("maestro.toml"),
    months: MonthsOption = 12,
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory for PNGs.")] = Path(
        "docs/assets/charts"
    ),
) -> None:
    """Render the DORA trend, PR size distribution, deploy heatmap and pipeline funnel as PNG files."""
    paths = RenderCharts(_provider(load_settings(config)), MatplotlibChartRenderer(), out).execute(
        DATASET_END, months
    )
    for p in paths:
        console.print(f"[green]✓[/] {p}")


@app.command()
def demo(config: ConfigOption = Path("maestro.toml")) -> None:
    """Run the whole phase-1 flow: seed → DORA → PR flow → charts."""
    seed(config)
    metrics_dora(config)
    metrics_pr_flow(config)
    charts(config)


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
    # Windows consoles often default to cp1252; Rich output uses UTF-8 symbols.
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
