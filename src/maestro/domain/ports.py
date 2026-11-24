"""Ports (interfaces) the application layer depends on. Implemented in `infrastructure`."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from maestro.domain.entities import Commit, Dataset, Deployment, Incident, Period, PullRequest, Repository


@runtime_checkable
class Clock(Protocol):
    """Source of time — injected so use cases are deterministic in tests."""

    def now(self) -> datetime: ...


class DevOpsProvider(Protocol):
    """Read-only access to engineering data (repositories, commits, PRs, deployments, incidents)."""

    def list_repositories(self) -> list[Repository]: ...

    def list_commits(self, repository_id: str, period: Period) -> list[Commit]: ...

    def list_pull_requests(self, repository_id: str, period: Period) -> list[PullRequest]: ...

    def list_deployments(self, repository_id: str, period: Period) -> list[Deployment]: ...

    def list_incidents(self, repository_id: str, period: Period) -> list[Incident]: ...

    def get_pull_request(self, pull_request_id: str) -> PullRequest | None: ...


class DatasetWriter(Protocol):
    """Persists a generated dataset so a `DevOpsProvider` can read it back."""

    def write(self, dataset: Dataset) -> Path: ...


class ChartRenderer(Protocol):
    """Turns already-computed series into image files. Knows nothing about how numbers were produced."""

    def line_grid(
        self,
        title: str,
        panels: list[tuple[str, str, dict[str, list[float]]]],
        x_labels: list[str],
        output: Path,
    ) -> Path:
        """`panels` = [(panel_title, y_label, {series_name: values}), ...] sharing `x_labels`."""
        ...

    def histogram(
        self, title: str, x_label: str, values: list[float], output: Path, bins: int = 20
    ) -> Path: ...

    def heatmap(
        self, title: str, rows: list[str], cols: list[str], matrix: list[list[float]], output: Path
    ) -> Path: ...

    def funnel(self, title: str, stages: list[tuple[str, int]], output: Path) -> Path: ...
