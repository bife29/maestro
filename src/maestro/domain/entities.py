"""Core entities of the engineering domain. Frozen dataclasses — values, not behaviour-heavy objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Severity(StrEnum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"


@dataclass(frozen=True, slots=True)
class Period:
    """Half-open interval [start, end)."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            msg = f"Period end must be after start (start={self.start}, end={self.end})"
            raise ValueError(msg)

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / 86_400

    @property
    def weeks(self) -> float:
        return self.days / 7


@dataclass(frozen=True, slots=True)
class Repository:
    id: str
    name: str
    language: str
    team: str


@dataclass(frozen=True, slots=True)
class Commit:
    sha: str
    repository_id: str
    authored_at: datetime
    author_id: str
    additions: int
    deletions: int
    files_changed: int
    pull_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChangedFile:
    path: str
    additions: int
    deletions: int
    patch: str = ""


@dataclass(frozen=True, slots=True)
class PullRequest:
    id: str
    repository_id: str
    title: str
    author_id: str
    created_at: datetime
    first_review_at: datetime | None
    merged_at: datetime | None
    review_rounds: int
    ai_reviewed: bool
    description: str = ""
    files: tuple[ChangedFile, ...] = field(default_factory=tuple)
    linked_work_items: tuple[str, ...] = field(default_factory=tuple)

    @property
    def files_changed(self) -> int:
        return len(self.files)

    @property
    def lines_changed(self) -> int:
        return sum(f.additions + f.deletions for f in self.files)

    @property
    def is_merged(self) -> bool:
        return self.merged_at is not None


@dataclass(frozen=True, slots=True)
class Deployment:
    id: str
    repository_id: str
    deployed_at: datetime
    commit_sha: str
    succeeded: bool
    environment: str = "production"


@dataclass(frozen=True, slots=True)
class Incident:
    id: str
    repository_id: str
    started_at: datetime
    resolved_at: datetime | None
    severity: Severity
    caused_by_deployment_id: str | None = None

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None


@dataclass(frozen=True, slots=True)
class Dataset:
    """In-memory aggregate of everything a DevOps provider can return. Used by the seed and tests."""

    repositories: tuple[Repository, ...]
    commits: tuple[Commit, ...]
    pull_requests: tuple[PullRequest, ...]
    deployments: tuple[Deployment, ...]
    incidents: tuple[Incident, ...]
