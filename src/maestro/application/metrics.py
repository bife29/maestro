"""Use cases computing DORA and PR-flow metrics through the `DevOpsProvider` port."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from maestro.domain.entities import Period, Repository
from maestro.domain.metrics import DoraMetrics, PrFlowMetrics, compute_dora, compute_pr_flow
from maestro.domain.ports import DevOpsProvider

WINDOW_DAYS = 30
COMMIT_LOOKBACK_DAYS = 120  # commits may predate the deployment window (lead time)


def month_windows(end: datetime, months: int) -> list[Period]:
    """`months` consecutive 30-day windows ending at `end`, oldest first."""
    windows: list[Period] = []
    cursor = end
    for _ in range(months):
        start = cursor - timedelta(days=WINDOW_DAYS)
        windows.append(Period(start, cursor))
        cursor = start
    return list(reversed(windows))


def _matches(repo: Repository, selector: str | None) -> bool:
    return selector is None or selector in (repo.id, repo.name)


@dataclass(frozen=True, slots=True)
class RepositoryDora:
    repository: Repository
    overall: DoraMetrics
    monthly: list[DoraMetrics]


class ComputeDora:
    def __init__(self, provider: DevOpsProvider) -> None:
        self.provider = provider

    def execute(self, end: datetime, months: int = 12, repository: str | None = None) -> list[RepositoryDora]:
        period = Period(end - timedelta(days=WINDOW_DAYS * months), end)
        windows = month_windows(end, months)
        results: list[RepositoryDora] = []
        for repo in self.provider.list_repositories():
            if not _matches(repo, repository):
                continue
            commit_period = Period(period.start - timedelta(days=COMMIT_LOOKBACK_DAYS), period.end)
            commits = self.provider.list_commits(repo.id, commit_period)
            deployments = self.provider.list_deployments(repo.id, period)
            incidents = self.provider.list_incidents(repo.id, period)
            results.append(
                RepositoryDora(
                    repository=repo,
                    overall=compute_dora(repo.id, period, commits, deployments, incidents),
                    monthly=[compute_dora(repo.id, w, commits, deployments, incidents) for w in windows],
                )
            )
        return results


@dataclass(frozen=True, slots=True)
class RepositoryPrFlow:
    repository: Repository
    metrics: PrFlowMetrics


class ComputePrFlow:
    def __init__(self, provider: DevOpsProvider) -> None:
        self.provider = provider

    def execute(
        self, end: datetime, months: int = 12, repository: str | None = None
    ) -> list[RepositoryPrFlow]:
        period = Period(end - timedelta(days=WINDOW_DAYS * months), end)
        return [
            RepositoryPrFlow(
                repo, compute_pr_flow(repo.id, period, self.provider.list_pull_requests(repo.id, period))
            )
            for repo in self.provider.list_repositories()
            if _matches(repo, repository)
        ]
