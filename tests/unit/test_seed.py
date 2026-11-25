"""Seed generator: determinism (RN-07), demo PRs and JSON round-trip through the local provider."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from maestro.application.seed import DEMO_LARGE_PR_ID, DEMO_SMALL_PR_ID, PROFILES, GenerateSeed
from maestro.domain.entities import Period
from maestro.infrastructure.devops.local_json import LocalJsonDatasetWriter, LocalJsonProvider

END = datetime(2026, 12, 1, tzinfo=UTC)


def test_same_seed_produces_identical_dataset() -> None:
    a = GenerateSeed(seed=7, months=3, end=END).execute()
    b = GenerateSeed(seed=7, months=3, end=END).execute()
    assert a == b


def test_different_seed_produces_different_dataset() -> None:
    assert (
        GenerateSeed(seed=1, months=2, end=END).execute() != GenerateSeed(seed=2, months=2, end=END).execute()
    )


def test_dataset_shape_and_demo_pull_requests() -> None:
    ds = GenerateSeed(seed=42, months=12, end=END).execute()
    assert len(ds.repositories) == len(PROFILES)
    assert all(r.name.startswith("atlas-") for r in ds.repositories)
    by_id = {p.id: p for p in ds.pull_requests}
    small, large = by_id[DEMO_SMALL_PR_ID], by_id[DEMO_LARGE_PR_ID]
    assert small.files_changed == 2 and "sk-live-" in small.files[0].patch
    assert large.files_changed == 80
    assert all(d.commit_sha in {c.sha for c in ds.commits} for d in ds.deployments)


def test_local_json_round_trip(tmp_path: Path) -> None:
    ds = GenerateSeed(seed=3, months=2, end=END).execute()
    LocalJsonDatasetWriter(tmp_path).write(ds)
    provider = LocalJsonProvider(tmp_path)
    period = Period(END - timedelta(days=60), END)
    repos = provider.list_repositories()
    assert [r.id for r in repos] == [r.id for r in ds.repositories]
    assert sum(len(provider.list_pull_requests(r.id, period)) for r in repos) == len(ds.pull_requests)
    assert provider.get_pull_request(DEMO_SMALL_PR_ID) == next(
        p for p in ds.pull_requests if p.id == DEMO_SMALL_PR_ID
    )
    assert provider.get_pull_request("PR-none") is None
