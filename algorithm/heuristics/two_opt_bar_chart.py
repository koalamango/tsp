"""Plot 2-opt gaps and mean execution time for 5 to 80 cities.

Run: python algorithm/heuristics/two_opt_bar_chart.py
Reads 2-opt summary reports in outputs/ and saves a PNG in outputs/charts/.
Execution time includes nearest-neighbour construction and 2-opt refinement.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[2]
CITY_COUNTS = (5, 10, 20, 40, 80)
ROW_LABELS = tuple(f"data set {index}" for index in range(1, 6)) + (
    "Average (5 data sets)",
)


def read_summary(path: Path) -> tuple[list[float], float]:
    """Read six gaps and the reported average execution time in seconds."""
    results = {}
    mean_seconds = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] not in ROW_LABELS:
            continue
        if cells[0] in results:
            raise ValueError(f"{path.name}: duplicate row {cells[0]!r}")
        if len(cells) != 5:
            raise ValueError(f"{path.name}: expected five columns in row {cells[0]!r}")
        percentage = cells[-1]
        if not percentage.endswith("%"):
            raise ValueError(f"{path.name}: expected a percentage in row {cells[0]!r}")
        value = float(percentage[:-1])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{path.name}: invalid percentage {percentage!r}")
        results[cells[0]] = value
        if cells[0] == ROW_LABELS[-1]:
            mean_seconds = float(cells[2])
            if not math.isfinite(mean_seconds) or mean_seconds < 0:
                raise ValueError(f"{path.name}: invalid mean execution time {cells[2]!r}")
    missing = [label for label in ROW_LABELS if label not in results]
    if missing:
        raise ValueError(f"{path.name}: missing rows: {', '.join(missing)}")
    return [results[label] for label in ROW_LABELS], mean_seconds


def create_chart(input_dir: Path, output: Path) -> None:
    """Plot six gap bars per city count and a mean-time line on a second axis."""
    summaries = [
        read_summary(input_dir / f"coordinates_{count}_cities_two_opt_summary.md")
        for count in CITY_COUNTS
    ]
    datasets = [gaps for gaps, _ in summaries]
    mean_microseconds = [seconds * 1_000_000 for _, seconds in summaries]
    fig, ax = plt.subplots(figsize=(14, 7), layout="constrained")
    width = 0.13
    colors = ["#4477AA", "#66CCEE", "#228833", "#CCBB44", "#EE6677", "#333333"]
    labels = [f"Data set {index}" for index in range(1, 6)] + ["Mean gap"]
    for series, (label, color) in enumerate(zip(labels, colors)):
        positions = [group + (series - 2.5) * width for group in range(len(CITY_COUNTS))]
        bars = ax.bar(
            positions, [values[series] for values in datasets], width,
            label=label, color=color, hatch="//" if series == 5 else None,
        )
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8, rotation=90)
    ax.set_xticks(range(len(CITY_COUNTS)), [f"{count} cities" for count in CITY_COUNTS])
    ax.set_xlabel("Number of cities")
    ax.set_ylabel("% above shortest possible route")
    ax.set_title("2-opt from nearest neighbour: route quality and mean execution time")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_ylim(bottom=0)
    ax.margins(y=0.18)
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.25)
    time_ax = ax.twinx()
    time_color = "#882255"
    time_ax.plot(range(len(CITY_COUNTS)), mean_microseconds,
                 color=time_color, marker="o", linewidth=2.5,
                 label="Mean execution time", markeredgecolor="white", markersize=8)
    time_ax.set_ylabel("Mean NN + 2-opt execution time (microseconds)", color=time_color)
    time_ax.tick_params(axis="y", colors=time_color)
    time_ax.set_ylim(bottom=0)
    time_ax.margins(y=0.25)
    for index, microseconds in enumerate(mean_microseconds):
        time_ax.annotate(f"{microseconds:.1f} µs", (index, microseconds),
                         xytext=(0, 10), textcoords="offset points", ha="center",
                         color=time_color, fontsize=9,
                         bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
    handles, legend_labels = ax.get_legend_handles_labels()
    time_handles, time_labels = time_ax.get_legend_handles_labels()
    ax.legend(handles + time_handles, legend_labels + time_labels,
              ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.10))
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "outputs",
                        help="Directory containing the five Markdown summary reports")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "outputs/charts/two_opt_gap_bar_chart.png",
                        help="Output chart filename (default: outputs/charts/two_opt_gap_bar_chart.png)")
    args = parser.parse_args()
    try:
        create_chart(args.input_dir, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Chart saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
