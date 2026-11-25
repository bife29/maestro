"""Use case: compute chart series from the provider and hand them to a `ChartRenderer` (SPEC F-04)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from maestro.application.metrics import WINDOW_DAYS, ComputeDora, month_windows
from maestro.domain.entities import Period
from maestro.domain.ports import ChartRenderer, DevOpsProvider

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOUR_BUCKETS = ["00-04", "04-08", "08-12", "12-16", "16-20", "20-24"]


class RenderCharts:
    def __init__(self, provider: DevOpsProvider, renderer: ChartRenderer, output_dir: Path) -> None:
        self.provider = provider
        self.renderer = renderer
        self.output_dir = output_dir

    def execute(self, end: datetime, months: int = 12) -> list[Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        period = Period(end - timedelta(days=WINDOW_DAYS * months), end)
        return [
            self._dora_trend(end, months),
            self._pr_size_distribution(period),
            self._deploy_heatmap(period),
            self._review_funnel(period),
        ]

    def _dora_trend(self, end: datetime, months: int) -> Path:
        results = ComputeDora(self.provider).execute(end, months)
        labels = [w.start.strftime("%b/%y") for w in month_windows(end, months)]

        def series(attr: str) -> dict[str, list[float]]:
            out: dict[str, list[float]] = {}
            for r in results:
                out[r.repository.name] = [
                    float(v) if (v := getattr(m, attr)) is not None else float("nan") for m in r.monthly
                ]
            return out

        panels = [
            ("Deployment frequency", "deploys / week", series("deployment_frequency_per_week")),
            ("Lead time for changes (p50)", "hours", series("lead_time_hours_p50")),
            ("Change failure rate", "ratio", series("change_failure_rate")),
            ("Time to restore (p50)", "hours", series("mttr_hours_p50")),
        ]
        return self.renderer.line_grid(
            "DORA metrics - monthly trend", panels, labels, self.output_dir / "dora_trend.png"
        )

    def _pr_size_distribution(self, period: Period) -> Path:
        values = [
            float(pr.lines_changed)
            for repo in self.provider.list_repositories()
            for pr in self.provider.list_pull_requests(repo.id, period)
        ]
        return self.renderer.histogram(
            "Pull request size distribution",
            "lines changed",
            values,
            self.output_dir / "pr_size_distribution.png",
        )

    def _deploy_heatmap(self, period: Period) -> Path:
        counts: Counter[tuple[int, int]] = Counter()
        for repo in self.provider.list_repositories():
            for d in self.provider.list_deployments(repo.id, period):
                counts[(d.deployed_at.weekday(), d.deployed_at.hour // 4)] += 1
        matrix = [[float(counts[(wd, hb)]) for hb in range(len(HOUR_BUCKETS))] for wd in range(7)]
        return self.renderer.heatmap(
            "Deployments by weekday x hour",
            WEEKDAYS,
            HOUR_BUCKETS,
            matrix,
            self.output_dir / "deploy_heatmap.png",
        )

    def _review_funnel(self, period: Period) -> Path:
        opened = reviewed = merged = deployed = clean = 0
        for repo in self.provider.list_repositories():
            deployments = {d.id for d in self.provider.list_deployments(repo.id, period)}
            incident_deploys = {
                i.caused_by_deployment_id
                for i in self.provider.list_incidents(repo.id, period)
                if i.caused_by_deployment_id
            }
            for pr in self.provider.list_pull_requests(repo.id, period):
                opened += 1
                reviewed += pr.first_review_at is not None
                merged += pr.is_merged
                dep_id = f"dep-{pr.id}"
                if dep_id in deployments:
                    deployed += 1
                    clean += dep_id not in incident_deploys
        stages = [
            ("Opened", opened),
            ("Reviewed", reviewed),
            ("Merged", merged),
            ("Deployed", deployed),
            ("Incident-free", clean),
        ]
        return self.renderer.funnel("Change pipeline funnel", stages, self.output_dir / "review_funnel.png")
