from pathlib import Path

from typer.testing import CliRunner

from maestro import __version__
from maestro.presentation.cli.app import app

runner = CliRunner()


def test_version_prints_package_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_runs_without_config(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--config", str(tmp_path / "none.toml")])
    assert result.exit_code == 0
    assert "devops.provider" in result.stdout
    assert "local" in result.stdout
