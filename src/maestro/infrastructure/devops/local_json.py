"""Local JSON adapter: writes a `Dataset` to disk and serves it back through the `DevOpsProvider` port."""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from maestro.domain.entities import (
    ChangedFile,
    Commit,
    Dataset,
    Deployment,
    Incident,
    Period,
    PullRequest,
    Repository,
    Severity,
)

_FILES = {
    "repositories": "repositories.json",
    "commits": "commits.json",
    "pull_requests": "pull_requests.json",
    "deployments": "deployments.json",
    "incidents": "incidents.json",
}


def _encode(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, tuple | list):
        return [_encode(x) for x in obj]
    return obj


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class LocalJsonDatasetWriter:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def write(self, dataset: Dataset) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for attr, filename in _FILES.items():
            payload = _encode(getattr(dataset, attr))
            (self.data_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
        return self.data_dir


class LocalJsonProvider:
    """`DevOpsProvider` backed by the JSON files produced by `LocalJsonDatasetWriter`. Loads lazily, once."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._dataset: Dataset | None = None

    def _load(self) -> Dataset:
        if self._dataset is None:
            if not (self.data_dir / _FILES["repositories"]).exists():
                msg = f"No dataset in {self.data_dir}. Run `maestro seed` first."
                raise FileNotFoundError(msg)
            raw = {k: json.loads((self.data_dir / v).read_text(encoding="utf-8")) for k, v in _FILES.items()}
            self._dataset = Dataset(
                repositories=tuple(Repository(**r) for r in raw["repositories"]),
                commits=tuple(
                    Commit(**{**c, "authored_at": datetime.fromisoformat(c["authored_at"])})
                    for c in raw["commits"]
                ),
                pull_requests=tuple(self._pr(p) for p in raw["pull_requests"]),
                deployments=tuple(
                    Deployment(**{**d, "deployed_at": datetime.fromisoformat(d["deployed_at"])})
                    for d in raw["deployments"]
                ),
                incidents=tuple(
                    Incident(
                        **{
                            **i,
                            "started_at": datetime.fromisoformat(i["started_at"]),
                            "resolved_at": _dt(i["resolved_at"]),
                            "severity": Severity(i["severity"]),
                        }
                    )
                    for i in raw["incidents"]
                ),
            )
        return self._dataset

    @staticmethod
    def _pr(p: dict[str, Any]) -> PullRequest:
        return PullRequest(
            **{
                **p,
                "created_at": datetime.fromisoformat(p["created_at"]),
                "first_review_at": _dt(p["first_review_at"]),
                "merged_at": _dt(p["merged_at"]),
                "files": tuple(ChangedFile(**f) for f in p["files"]),
                "linked_work_items": tuple(p["linked_work_items"]),
            }
        )

    def list_repositories(self) -> list[Repository]:
        return list(self._load().repositories)

    def list_commits(self, repository_id: str, period: Period) -> list[Commit]:
        return [
            c
            for c in self._load().commits
            if c.repository_id == repository_id and period.contains(c.authored_at)
        ]

    def list_pull_requests(self, repository_id: str, period: Period) -> list[PullRequest]:
        return [
            p
            for p in self._load().pull_requests
            if p.repository_id == repository_id and period.contains(p.created_at)
        ]

    def list_deployments(self, repository_id: str, period: Period) -> list[Deployment]:
        return [
            d
            for d in self._load().deployments
            if d.repository_id == repository_id and period.contains(d.deployed_at)
        ]

    def list_incidents(self, repository_id: str, period: Period) -> list[Incident]:
        return [
            i
            for i in self._load().incidents
            if i.repository_id == repository_id and period.contains(i.started_at)
        ]

    def get_pull_request(self, pull_request_id: str) -> PullRequest | None:
        return next((p for p in self._load().pull_requests if p.id == pull_request_id), None)


__all__ = ["LocalJsonDatasetWriter", "LocalJsonProvider", "asdict"]
