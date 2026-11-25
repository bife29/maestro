"""DORA and PR-flow metrics — pure functions over domain entities.

Thresholds follow the DORA "Accelerate State of DevOps" performance clusters. The *overall* level is the
**worst** of the four metrics: a team is only as fast as its slowest capability. That rule is deliberate and
documented here so dashboards never hide a weak metric behind three strong ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from statistics import median

from maestro.domain.entities import Commit, Deployment, Incident, Period, PullRequest

HOURS_PER_DAY = 24.0
HOURS_PER_WEEK = 168.0
HOURS_PER_MONTH = 730.0


class DoraLevel(StrEnum):
    ELITE = "elite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_LEVEL_RANK = {DoraLevel.ELITE: 0, DoraLevel.HIGH: 1, DoraLevel.MEDIUM: 2, DoraLevel.LOW: 3}


def worst(*levels: DoraLevel) -> DoraLevel:
    return max(levels, key=lambda lv: _LEVEL_RANK[lv])


def classify_deployment_frequency(per_week: float) -> DoraLevel:
    """Elite: on demand (>= daily) · High: weekly to daily · Medium: monthly to weekly · Low: < monthly."""
    if per_week >= 7:
        return DoraLevel.ELITE
    if per_week >= 1:
        return DoraLevel.HIGH
    if per_week >= 7 / 30:
        return DoraLevel.MEDIUM
    return DoraLevel.LOW


def classify_lead_time(hours: float | None) -> DoraLevel:
    """Elite: < 1 day · High: 1 day to 1 week · Medium: 1 week to 1 month · Low: > 1 month."""
    if hours is None:
        return DoraLevel.LOW
    if hours < HOURS_PER_DAY:
        return DoraLevel.ELITE
    if hours < HOURS_PER_WEEK:
        return DoraLevel.HIGH
    if hours < HOURS_PER_MONTH:
        return DoraLevel.MEDIUM
    return DoraLevel.LOW


def classify_change_failure_rate(rate: float) -> DoraLevel:
    """Elite: ≤ 5 % · High: ≤ 10 % · Medium: ≤ 15 % · Low: > 15 %."""
    if rate <= 0.05:
        return DoraLevel.ELITE
    if rate <= 0.10:
        return DoraLevel.HIGH
    if rate <= 0.15:
        return DoraLevel.MEDIUM
    return DoraLevel.LOW


def classify_mttr(hours: float | None) -> DoraLevel:
    """Elite: < 1 h · High: < 1 day · Medium: < 1 week · Low: ≥ 1 week or never restored."""
    if hours is None:
        return DoraLevel.LOW
    if hours < 1:
        return DoraLevel.ELITE
    if hours < HOURS_PER_DAY:
        return DoraLevel.HIGH
    if hours < HOURS_PER_WEEK:
        return DoraLevel.MEDIUM
    return DoraLevel.LOW


@dataclass(frozen=True, slots=True)
class DoraMetrics:
    repository_id: str
    period: Period
    deployments: int
    failed_deployments: int
    deployment_frequency_per_week: float
    lead_time_hours_p50: float | None
    change_failure_rate: float
    mttr_hours_p50: float | None
    incidents: int

    @property
    def frequency_level(self) -> DoraLevel:
        return classify_deployment_frequency(self.deployment_frequency_per_week)

    @property
    def lead_time_level(self) -> DoraLevel:
        return classify_lead_time(self.lead_time_hours_p50)

    @property
    def cfr_level(self) -> DoraLevel:
        return classify_change_failure_rate(self.change_failure_rate)

    @property
    def mttr_level(self) -> DoraLevel:
        return classify_mttr(self.mttr_hours_p50)

    @property
    def overall_level(self) -> DoraLevel:
        return worst(self.frequency_level, self.lead_time_level, self.cfr_level, self.mttr_level)


def _hours(delta_seconds: float) -> float:
    return delta_seconds / 3600


def compute_dora(
    repository_id: str,
    period: Period,
    commits: list[Commit],
    deployments: list[Deployment],
    incidents: list[Incident],
) -> DoraMetrics:
    """Compute the four DORA metrics for one repository inside `period`.

    * Lead time = deployed_at - authored_at of the deployed commit (median).
    * Change failure rate = deployments that failed **or** caused an incident / deployments.
    * MTTR = resolved_at - started_at of incidents started in the period (median); unresolved ones are
      excluded from the median but still counted in `incidents`.
    """
    deploys = [d for d in deployments if d.repository_id == repository_id and period.contains(d.deployed_at)]
    incs = [i for i in incidents if i.repository_id == repository_id and period.contains(i.started_at)]
    commit_by_sha = {c.sha: c for c in commits if c.repository_id == repository_id}

    lead_times = [
        _hours((d.deployed_at - commit_by_sha[d.commit_sha].authored_at).total_seconds())
        for d in deploys
        if d.commit_sha in commit_by_sha
    ]
    deploys_with_incident = {i.caused_by_deployment_id for i in incs if i.caused_by_deployment_id}
    failed = sum(1 for d in deploys if not d.succeeded or d.id in deploys_with_incident)
    restore_times = [_hours((i.resolved_at - i.started_at).total_seconds()) for i in incs if i.resolved_at]

    return DoraMetrics(
        repository_id=repository_id,
        period=period,
        deployments=len(deploys),
        failed_deployments=failed,
        deployment_frequency_per_week=len(deploys) / period.weeks if period.weeks else 0.0,
        lead_time_hours_p50=median(lead_times) if lead_times else None,
        change_failure_rate=failed / len(deploys) if deploys else 0.0,
        mttr_hours_p50=median(restore_times) if restore_times else None,
        incidents=len(incs),
    )


@dataclass(frozen=True, slots=True)
class PrFlowMetrics:
    repository_id: str
    period: Period
    opened: int
    merged: int
    time_to_first_review_hours_p50: float | None
    cycle_time_hours_p50: float | None
    size_files_mean: float
    size_lines_mean: float
    rework_rate: float
    ai_reviewed_rate: float


def compute_pr_flow(repository_id: str, period: Period, pull_requests: list[PullRequest]) -> PrFlowMetrics:
    """PR-flow health: review latency, cycle time, size and rework (PRs needing > 2 review rounds)."""
    prs = [p for p in pull_requests if p.repository_id == repository_id and period.contains(p.created_at)]
    merged = [p for p in prs if p.merged_at is not None]
    ttfr = [_hours((p.first_review_at - p.created_at).total_seconds()) for p in prs if p.first_review_at]
    cycle = [_hours((p.merged_at - p.created_at).total_seconds()) for p in merged if p.merged_at]
    n = len(prs)
    return PrFlowMetrics(
        repository_id=repository_id,
        period=period,
        opened=n,
        merged=len(merged),
        time_to_first_review_hours_p50=median(ttfr) if ttfr else None,
        cycle_time_hours_p50=median(cycle) if cycle else None,
        size_files_mean=sum(p.files_changed for p in prs) / n if n else 0.0,
        size_lines_mean=sum(p.lines_changed for p in prs) / n if n else 0.0,
        rework_rate=sum(1 for p in prs if p.review_rounds > 2) / n if n else 0.0,
        ai_reviewed_rate=sum(1 for p in prs if p.ai_reviewed) / n if n else 0.0,
    )
