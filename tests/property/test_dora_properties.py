"""Property-based invariants of the DORA computation (hypothesis)."""

from datetime import UTC, datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from maestro.domain.entities import Commit, Deployment, Incident, Period, Severity
from maestro.domain.metrics import compute_dora

T0 = datetime(2026, 1, 1, tzinfo=UTC)
PERIOD = Period(T0, T0 + timedelta(days=30))

deploy_offsets = st.lists(st.integers(min_value=0, max_value=29 * 24), min_size=0, max_size=40)
success_flags = st.lists(st.booleans(), min_size=40, max_size=40)


def _build(offsets: list[int], flags: list[bool]) -> tuple[list[Commit], list[Deployment]]:
    commits, deploys = [], []
    for i, (h, ok) in enumerate(zip(offsets, flags, strict=False)):
        sha = f"sha{i}"
        commits.append(Commit(sha, "r1", T0, "dev", 1, 0, 1))
        deploys.append(Deployment(f"d{i}", "r1", T0 + timedelta(hours=h), sha, ok))
    return commits, deploys


@settings(max_examples=60)
@given(deploy_offsets, success_flags)
def test_rates_are_bounded_and_counts_consistent(offsets: list[int], flags: list[bool]) -> None:
    commits, deploys = _build(offsets, flags)
    m = compute_dora("r1", PERIOD, commits, deploys, [])
    assert 0.0 <= m.change_failure_rate <= 1.0
    assert m.deployment_frequency_per_week >= 0.0
    assert m.failed_deployments <= m.deployments == len(deploys)
    assert (m.lead_time_hours_p50 is None) == (not deploys)
    if m.lead_time_hours_p50 is not None:
        assert m.lead_time_hours_p50 >= 0.0


@settings(max_examples=40)
@given(deploy_offsets, success_flags)
def test_adding_a_failed_deployment_never_lowers_the_failure_rate(
    offsets: list[int], flags: list[bool]
) -> None:
    commits, deploys = _build(offsets, flags)
    before = compute_dora("r1", PERIOD, commits, deploys, []).change_failure_rate
    extra = Deployment("d-extra", "r1", T0 + timedelta(hours=1), "sha-extra", succeeded=False)
    after = compute_dora("r1", PERIOD, commits, [*deploys, extra], []).change_failure_rate
    assert after >= before


@settings(max_examples=40)
@given(st.lists(st.integers(min_value=1, max_value=200), min_size=1, max_size=20))
def test_mttr_is_within_min_and_max_restore_times(durations_h: list[int]) -> None:
    incidents = [
        Incident(f"i{i}", "r1", T0 + timedelta(hours=1), T0 + timedelta(hours=1 + d), Severity.SEV2)
        for i, d in enumerate(durations_h)
    ]
    m = compute_dora("r1", PERIOD, [], [], incidents)
    assert m.mttr_hours_p50 is not None
    assert min(durations_h) <= m.mttr_hours_p50 <= max(durations_h)
