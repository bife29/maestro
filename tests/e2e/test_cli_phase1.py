"""End-to-end: seed -> metrics -> charts through the CLI on a temporary config."""

from pathlib import Path

from typer.testing import CliRunner

from maestro.presentation.cli.app import app

runner = CliRunner()


def _config(tmp_path: Path) -> Path:
    cfg = tmp_path / "maestro.toml"
    data_dir = (tmp_path / "data").as_posix()
    cfg.write_text(
        f'[devops]\nprovider = "local"\ndata_dir = "{data_dir}"\n[seed]\ndefault = 11\nmonths = 3\n',
        encoding="utf-8",
    )
    return cfg


def test_seed_metrics_and_charts_flow(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    assert runner.invoke(app, ["seed", "--config", str(cfg)]).exit_code == 0
    assert (tmp_path / "data" / "pull_requests.json").exists()

    dora = runner.invoke(app, ["metrics", "dora", "--config", str(cfg), "--months", "3", "--json"])
    assert dora.exit_code == 0
    assert "atlas-payments-api" in dora.stdout and "overall_level" in dora.stdout

    flow = runner.invoke(
        app, ["metrics", "pr-flow", "--config", str(cfg), "--months", "3", "--repo", "repo-01", "--json"]
    )
    assert flow.exit_code == 0
    assert "atlas-payments-api" in flow.stdout and "rework_rate" in flow.stdout

    table = runner.invoke(app, ["metrics", "pr-flow", "--config", str(cfg), "--months", "3"])
    assert table.exit_code == 0 and "Pull-request flow" in table.stdout

    out = tmp_path / "charts"
    charts = runner.invoke(app, ["charts", "--config", str(cfg), "--months", "3", "--out", str(out)])
    assert charts.exit_code == 0
    assert {p.name for p in out.glob("*.png")} == {
        "dora_trend.png",
        "pr_size_distribution.png",
        "deploy_heatmap.png",
        "review_funnel.png",
    }


def test_metrics_without_dataset_fails_with_hint(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    result = runner.invoke(app, ["metrics", "dora", "--config", str(cfg)])
    assert result.exit_code != 0
    assert isinstance(result.exception, FileNotFoundError)
    assert "maestro seed" in str(result.exception)
