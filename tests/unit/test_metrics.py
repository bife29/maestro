"""Unit tests for the pure DORA / PR-flow functions in the domain layer."""

from datetime import UTC, datetime, timedelta

import pytest

from maestro.domain.entities import Commit, Deployment, Incident, Period, Severity
from maestro.domain.metrics import (
    DoraLevel,
    classify_change_failure_rate,
    classify_deployment_frequency,
    classify_lead_time,
    classify_mttr,
    compute_dora,
    worst,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
PERIOD = Period(T0, T0 + timedelta(days=30))


def _commit(sha: str, when: datetime) -> Commit:
    return Commit(sha, "r1", when, "dev-1", 10, 2, 1, "PR-1")


def _deploy(dep_id: str, when: datetime, sha: str, ok: bool = True) -> Deployment:
    return Deployment(dep_id, "r1", when, sha, ok)


def test_zero_deployments_yield_zero_frequency_and_no_lead_time() -> None:
    m = compute_dora("r1", PERIOD, [], [], [])
    assert m.deployments == 0
    assert m.deployment_frequency_per_week == 0.0
    assert m.lead_time_hours_p50 is None
    assert m.change_failure_rate == 0.0
    assert m.overall_level == DoraLevel.LOW


def test_lead_time_is_median_of_commit_to_deploy_hours() -> None:
    commits = [_commit("a", T0), _commit("b", T0)]
    deployments = [_deploy("d1", T0 + timedelta(hours=2), "a"), _deploy("d2", T0 + timedelta(hours=10), "b")]
    m = compute_dora("r1", PERIOD, commits, deployments, [])
    assert m.lead_time_hours_p50 == 6.0
    assert m.deployments == 2


def test_incident_caused_by_deployment_counts_as_failure_even_if_deploy_succeeded() -> None:
    deployments = [_deploy("d1", T0 + timedelta(days=1), "a"), _deploy("d2", T0 + timedelta(days=2), "b")]
    incidents = [Incident("i1", "r1", T0 + timedelta(days=1, hours=1), None, Severity.SEV1, "d1")]
    m = compute_dora("r1", PERIOD, [], deployments, incidents)
    assert m.failed_deployments == 1
    assert m.change_failure_rate == 0.5
    assert m.incidents == 1
    assert m.mttr_hours_p50 is None  # unresolved incident has no restore time


def test_events_outside_period_are_ignored() -> None:
    outside = PERIOD.end + timedelta(days=1)
    m = compute_dora("r1", PERIOD, [], [_deploy("d1", outside, "a", ok=False)], [])
    assert m.deployments == 0


def test_period_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="after start"):
        Period(T0, T0)


def test_classification_thresholds() -> None:
    assert classify_deployment_frequency(7) == DoraLevel.ELITE
    assert classify_deployment_frequency(1) == DoraLevel.HIGH
    assert classify_deployment_frequency(0.25) == DoraLevel.MEDIUM
    assert classify_deployment_frequency(0.1) == DoraLevel.LOW
    assert classify_lead_time(23.9) == DoraLevel.ELITE
    assert classify_lead_time(24) == DoraLevel.HIGH
    assert classify_lead_time(None) == DoraLevel.LOW
    assert classify_change_failure_rate(0.05) == DoraLevel.ELITE
    assert classify_change_failure_rate(0.151) == DoraLevel.LOW
    assert classify_mttr(0.5) == DoraLevel.ELITE
    assert classify_mttr(169) == DoraLevel.LOW


def test_overall_is_the_worst_level() -> None:
    assert worst(DoraLevel.ELITE, DoraLevel.HIGH, DoraLevel.LOW) == DoraLevel.LOW
    assert worst(DoraLevel.ELITE, DoraLevel.ELITE) == DoraLevel.ELITE
