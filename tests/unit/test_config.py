from pathlib import Path

from maestro.infrastructure.config import Settings, load_settings


def test_defaults_when_config_missing(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.devops.provider == "local"
    assert settings.llm.provider == "dry"
    assert settings.review.max_files == 50


def test_toml_values_are_loaded(tmp_path: Path) -> None:
    cfg = tmp_path / "maestro.toml"
    cfg.write_text('[review]\nmax_files = 10\n[llm]\nprovider = "openai_compatible"\n', encoding="utf-8")
    settings = load_settings(cfg)
    assert settings.review.max_files == 10
    assert settings.llm.provider == "openai_compatible"


def test_env_overrides_toml(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "maestro.toml"
    cfg.write_text("[review]\nmax_lines = 100\n", encoding="utf-8")
    monkeypatch.setenv("MAESTRO_REVIEW__MAX_LINES", "7")
    assert load_settings(cfg).review.max_lines == 7


def test_settings_ignore_unknown_keys() -> None:
    assert Settings(unknown="x").devops.provider == "local"  # type: ignore[call-arg]
