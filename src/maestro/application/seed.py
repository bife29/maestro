"""Deterministic synthetic dataset generator (SPEC F-01, RN-07).

Everything here is fictional: a made-up company ("Atlas"), six repositories, pseudonymous developers
(`dev-01`…), and two hand-crafted demo pull requests used by later phases:

* `PR-07` — small Python change with two planted findings (hard-coded secret, SQL built by concatenation).
* `PR-13` — oversized change (80 files) that must trip the size gate without calling any LLM.

Profiles are tuned so the six repositories land on different DORA levels, which makes the charts didactic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from maestro.domain.entities import (
    ChangedFile,
    Commit,
    Dataset,
    Deployment,
    Incident,
    PullRequest,
    Repository,
    Severity,
)

DEMO_SMALL_PR_ID = "PR-07"
DEMO_LARGE_PR_ID = "PR-13"


@dataclass(frozen=True, slots=True)
class _ChangeContext:
    repo: Repository
    devs: list[str]
    pr_id: str
    created: datetime
    profile: RepoProfile


@dataclass(frozen=True, slots=True)
class RepoProfile:
    name: str
    language: str
    team: str
    prs_per_week: float
    lead_time_hours: float  # mean commit → deploy
    change_failure_rate: float
    mttr_hours: float
    review_latency_hours: float
    ai_review_share: float


# Six profiles → roughly one Elite, two High, two Medium, one Low.
PROFILES: tuple[RepoProfile, ...] = (
    RepoProfile("atlas-payments-api", "python", "payments", 9.0, 10.0, 0.03, 0.6, 1.5, 0.9),
    RepoProfile("atlas-ledger-worker", "python", "payments", 4.0, 40.0, 0.07, 6.0, 4.0, 0.8),
    RepoProfile("atlas-onboarding-web", "typescript", "growth", 5.0, 60.0, 0.09, 12.0, 6.0, 0.6),
    RepoProfile("atlas-notifications-consumer", "csharp", "platform", 1.5, 200.0, 0.12, 40.0, 20.0, 0.4),
    RepoProfile("atlas-risk-engine", "python", "risk", 1.0, 320.0, 0.14, 70.0, 30.0, 0.3),
    RepoProfile("atlas-platform-infra", "hcl", "platform", 0.4, 900.0, 0.22, 200.0, 48.0, 0.1),
)

PR_TITLES = (
    "feat: add idempotency key to {noun} endpoint",
    "fix: handle null {noun} on retry path",
    "refactor: extract {noun} mapper",
    "chore: bump dependencies for {noun} module",
    "test: property tests for {noun} calculator",
    "perf: cache {noun} lookups",
    "docs: runbook for {noun} incidents",
)
NOUNS = ("settlement", "ledger", "webhook", "statement", "limit", "onboarding", "notification", "risk score")


def _sha(rng: random.Random) -> str:
    return "".join(rng.choices("0123456789abcdef", k=40))


def _gauss_pos(rng: random.Random, mean: float, spread: float = 0.45) -> float:
    """Positive, right-skewed sample around `mean` (log-normal flavour without numpy)."""
    return max(0.05, rng.lognormvariate(0.0, spread) * mean)


class GenerateSeed:
    """Use case: build a `Dataset` for `months` months ending at `end` using `seed`."""

    def __init__(self, seed: int = 42, months: int = 12, end: datetime | None = None) -> None:
        self.seed = seed
        self.months = months
        self.end = end or datetime(2026, 12, 1, tzinfo=UTC)

    def execute(self) -> Dataset:
        rng = random.Random(self.seed)  # noqa: S311 — deterministic synthetic data, not security
        start = self.end - timedelta(days=30 * self.months)
        repos: list[Repository] = []
        commits: list[Commit] = []
        prs: list[PullRequest] = []
        deploys: list[Deployment] = []
        incidents: list[Incident] = []
        pr_counter = 0

        for idx, profile in enumerate(PROFILES, start=1):
            repo = Repository(
                id=f"repo-{idx:02d}", name=profile.name, language=profile.language, team=profile.team
            )
            repos.append(repo)
            devs = [f"dev-{idx:02d}-{n}" for n in range(1, 4)]
            total_prs = max(3, round(profile.prs_per_week * self.months * 30 / 7))
            for _ in range(total_prs):
                pr_counter += 1
                pr_id = f"PR-{pr_counter:02d}"
                created = start + timedelta(
                    seconds=rng.uniform(0, (self.end - start).total_seconds() - 3 * 86_400)
                )
                pr, pr_commits, deploy, incident = self._build_change(
                    rng, _ChangeContext(repo=repo, devs=devs, pr_id=pr_id, created=created, profile=profile)
                )
                prs.append(pr)
                commits.extend(pr_commits)
                if deploy:
                    deploys.append(deploy)
                if incident:
                    incidents.append(incident)

        prs = [self._apply_demo_overrides(p) for p in prs]
        return Dataset(
            repositories=tuple(repos),
            commits=tuple(sorted(commits, key=lambda c: c.authored_at)),
            pull_requests=tuple(sorted(prs, key=lambda p: p.created_at)),
            deployments=tuple(sorted(deploys, key=lambda d: d.deployed_at)),
            incidents=tuple(sorted(incidents, key=lambda i: i.started_at)),
        )

    def _build_change(
        self, rng: random.Random, ctx: _ChangeContext
    ) -> tuple[PullRequest, list[Commit], Deployment | None, Incident | None]:
        repo, devs, pr_id, created, profile = ctx.repo, ctx.devs, ctx.pr_id, ctx.created, ctx.profile
        author = rng.choice(devs)
        n_files = max(1, int(_gauss_pos(rng, 6.0, 0.7)))
        kinds = ("service", "repo", "handler", "model")
        files = tuple(
            ChangedFile(
                path=f"src/{rng.choice(NOUNS).replace(' ', '_')}/{rng.choice(kinds)}_{k}.py",
                additions=int(_gauss_pos(rng, 25.0, 0.8)),
                deletions=int(_gauss_pos(rng, 8.0, 0.8)),
            )
            for k in range(n_files)
        )
        first_commit_at = created - timedelta(hours=_gauss_pos(rng, 6.0))
        n_commits = rng.randint(1, 5)
        pr_commits = [
            Commit(
                sha=_sha(rng),
                repository_id=repo.id,
                authored_at=first_commit_at + timedelta(hours=k * rng.uniform(0.5, 6)),
                author_id=author,
                additions=sum(f.additions for f in files) // n_commits,
                deletions=sum(f.deletions for f in files) // n_commits,
                files_changed=n_files,
                pull_request_id=pr_id,
            )
            for k in range(n_commits)
        ]
        first_review = created + timedelta(hours=_gauss_pos(rng, profile.review_latency_hours))
        review_rounds = 1 + (rng.random() < 0.25) + (rng.random() < 0.10)
        merged = rng.random() < 0.92
        merged_at = (
            first_review + timedelta(hours=_gauss_pos(rng, profile.lead_time_hours * 0.5) * review_rounds)
            if merged
            else None
        )
        pr = PullRequest(
            id=pr_id,
            repository_id=repo.id,
            title=rng.choice(PR_TITLES).format(noun=rng.choice(NOUNS)),
            author_id=author,
            created_at=created,
            first_review_at=first_review,
            merged_at=merged_at,
            review_rounds=review_rounds,
            ai_reviewed=rng.random() < profile.ai_review_share,
            files=files,
            linked_work_items=(f"WI-{rng.randint(1000, 9999)}",),
        )
        if merged_at is None or merged_at >= self.end:
            return pr, pr_commits, None, None

        deployed_at = merged_at + timedelta(hours=_gauss_pos(rng, profile.lead_time_hours * 0.5))
        if deployed_at >= self.end:
            return pr, pr_commits, None, None
        failed = rng.random() < profile.change_failure_rate
        deploy = Deployment(
            id=f"dep-{pr_id}",
            repository_id=repo.id,
            deployed_at=deployed_at,
            commit_sha=pr_commits[-1].sha,
            succeeded=not (failed and rng.random() < 0.3),
        )
        incident = None
        if failed:
            started = deployed_at + timedelta(minutes=rng.uniform(5, 240))
            resolved = started + timedelta(hours=_gauss_pos(rng, profile.mttr_hours))
            incident = Incident(
                id=f"inc-{pr_id}",
                repository_id=repo.id,
                started_at=started,
                resolved_at=resolved if resolved < self.end else None,
                severity=rng.choice(tuple(Severity)),
                caused_by_deployment_id=deploy.id,
            )
        return pr, pr_commits, deploy, incident

    @staticmethod
    def _apply_demo_overrides(pr: PullRequest) -> PullRequest:
        """Replace two PRs by hand-crafted demo payloads with real diff content (used in phases 4+)."""
        if pr.id == DEMO_SMALL_PR_ID:
            return PullRequest(
                id=pr.id,
                repository_id=pr.repository_id,
                title="feat: settlement export endpoint",
                author_id=pr.author_id,
                created_at=pr.created_at,
                first_review_at=pr.first_review_at,
                merged_at=None,
                review_rounds=1,
                ai_reviewed=False,
                description="Adds CSV export for settlements. Closes WI-4711.",
                files=(
                    ChangedFile(
                        "src/settlement/export_service.py",
                        18,
                        0,
                        patch=(
                            "+import sqlite3\n"
                            "+\n"
                            # Planted finding for the review-agent demo (phase 4); not a real credential.
                            '+API_KEY = "sk-live-9f8e7d6c5b4a3f2e1d0c"\n'  # gitleaks:allow
                            "+\n"
                            "+def export_settlements(conn: sqlite3.Connection, merchant_id: str) -> list:\n"
                            "+    query = (\n"
                            '+        "SELECT * FROM settlements WHERE merchant_id = \'"\n'
                            '+        + merchant_id + "\'"\n'
                            "+    )\n"
                            "+    return conn.execute(query).fetchall()\n"
                        ),
                    ),
                    ChangedFile(
                        "src/settlement/routes.py",
                        9,
                        1,
                        patch=(
                            "+@router.get('/settlements/export')\n"
                            "+def export(merchant_id: str):\n"
                            "+    return export_settlements(get_conn(), merchant_id)\n"
                        ),
                    ),
                ),
                linked_work_items=("WI-4711",),
            )
        if pr.id == DEMO_LARGE_PR_ID:
            files = tuple(
                ChangedFile(f"src/ledger/module_{k:02d}.py", 60, 25, patch="+# large refactor chunk\n")
                for k in range(80)
            )
            return PullRequest(
                id=pr.id,
                repository_id=pr.repository_id,
                title="refactor: ledger module restructuring (big bang)",
                author_id=pr.author_id,
                created_at=pr.created_at,
                first_review_at=pr.first_review_at,
                merged_at=None,
                review_rounds=1,
                ai_reviewed=False,
                description="Moves 80 modules into the new ledger package layout.",
                files=files,
                linked_work_items=("WI-5100", "WI-5101"),
            )
        return pr
