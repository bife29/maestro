"""Matplotlib implementation of the `ChartRenderer` port. Headless (Agg) so it works in CI."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

PALETTE = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#64748b"]
plt.rcParams.update(
    {
        "figure.dpi": 130,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


class MatplotlibChartRenderer:
    def line_grid(
        self,
        title: str,
        panels: list[tuple[str, str, dict[str, list[float]]]],
        x_labels: list[str],
        output: Path,
    ) -> Path:
        cols = 2
        rows = math.ceil(len(panels) / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(13, 4.2 * rows), squeeze=False)
        flat = list(axes.flat)
        for ax, (panel_title, y_label, series) in zip(flat, panels, strict=False):
            for idx, (name, values) in enumerate(series.items()):
                ax.plot(
                    x_labels,
                    values,
                    marker="o",
                    linewidth=1.8,
                    markersize=3.5,
                    label=name,
                    color=PALETTE[idx % len(PALETTE)],
                )
            ax.set_title(panel_title, fontsize=12, fontweight="bold")
            ax.set_ylabel(y_label)
            ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        for ax in flat[len(panels) :]:
            ax.axis("off")
        handles, labels = flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 6), frameon=False, fontsize=9)
        fig.suptitle(title, fontsize=15, fontweight="bold")
        fig.tight_layout(rect=(0, 0.06, 1, 0.96))
        return self._save(fig, output)

    def histogram(self, title: str, x_label: str, values: list[float], output: Path, bins: int = 20) -> Path:
        fig, ax = plt.subplots(figsize=(10, 5))
        if values:
            ax.hist(values, bins=bins, color=PALETTE[0], alpha=0.85, edgecolor="white")
            p50 = sorted(values)[len(values) // 2]
            ax.axvline(p50, color=PALETTE[3], linestyle="--", linewidth=1.5, label=f"median = {p50:.0f}")
            ax.legend(frameon=False)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel(x_label)
        ax.set_ylabel("pull requests")
        fig.tight_layout()
        return self._save(fig, output)

    def heatmap(
        self, title: str, rows: list[str], cols: list[str], matrix: list[list[float]], output: Path
    ) -> Path:
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.grid(False)
        im = ax.imshow(matrix, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(cols)), labels=cols)
        ax.set_yticks(range(len(rows)), labels=rows)
        vmax = max((v for row in matrix for v in row), default=0.0)
        for r, row in enumerate(matrix):
            for c, value in enumerate(row):
                color = "white" if value > vmax * 0.6 else "#0f172a"
                ax.text(c, r, f"{value:.0f}", ha="center", va="center", fontsize=9, color=color)
        fig.colorbar(im, ax=ax, label="deployments")
        ax.set_title(title, fontsize=14, fontweight="bold")
        fig.tight_layout()
        return self._save(fig, output)

    def funnel(self, title: str, stages: list[tuple[str, int]], output: Path) -> Path:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.grid(False)
        top = stages[0][1] if stages and stages[0][1] else 1
        for idx, (name, count) in enumerate(stages):
            width = count / top
            ax.barh(
                idx, width, left=(1 - width) / 2, height=0.75, color=PALETTE[idx % len(PALETTE)], alpha=0.9
            )
            ax.text(0.5, idx, f"{name}: {count} ({count / top:.0%})", ha="center", va="center", color="white")
        ax.set_xlim(0, 1)
        ax.set_yticks([])
        ax.set_xticks([])
        ax.invert_yaxis()
        ax.set_title(title, fontsize=14, fontweight="bold")
        fig.tight_layout()
        return self._save(fig, output)

    @staticmethod
    def _save(fig: Figure, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, bbox_inches="tight")
        plt.close(fig)
        return output
