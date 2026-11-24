"""Architecture contract (constitution P3): layer direction is enforced by import-linter.

This test shells out to `lint-imports` so a violation fails the regular test run, not only CI.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("lint-imports") is None, reason="import-linter not installed")
def test_import_linter_contracts_hold() -> None:
    result = subprocess.run(
        ["lint-imports"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
