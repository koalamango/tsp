"""
tsp_charts.py - Matplotlib chart helpers for the tsp_loader and metaheuristic reports.

All functions take plain Python data (labels, numbers, and result dictionaries) so this
module does not depend on tsp_loader.py or metaheuristic.py. Charts are rendered headlessly
(Agg backend) and saved as PNG files, which the Markdown reports link to with relative
image paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")  # Headless: charts are written to files, never shown in a window
import matplotlib.pyplot as plt  # noqa: E402

from tsp_utils import format_duration

# (min, mean, max) of a series of measurements
Triple = Tuple[float, float, float]

_MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*", "h"]

# Shared Tableau 10 colour palette and styling constants
_COLOR_BLUE = "#4C78A8"
_COLOR_ORANGE = "#F28E2B"
_COLOR_GREEN = "#59A14F"
_COLOR_RED = "#E15759"
_COLOR_OPTIMUM = "grey"
_GRID_ALPHA = 0.3


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _configure_hbar_axes(
    ax,
    labels: Sequence[str],
    title: str,
    xlabel: str,
) -> List[int]:
    """Configure shared y-ticks, labels, title, and grid for horizontal bar charts."""
    positions = list(range(len(labels)))
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", which="major", alpha=_GRID_ALPHA)
    return positions


def _annotate_bars(
    ax,
    positions: Sequence[float],
    x_coords: Sequence[float],
    texts: Sequence[str],
    offset: int = 4,
    fontsize: int = 8,
) -> None:
    """Place value annotations to the right of horizontal bars."""
    for pos, x, text in zip(positions, x_coords, texts):
        ax.annotate(
            text, (x, pos), xytext=(offset, 0), textcoords="offset points",
            va="center", fontsize=fontsize,
        )


def save_runtime_bar_chart(
    path: Path,
    title: str,
    labels: Sequence[str],
    runtimes: Sequence[Triple],
) -> Path:
    """Horizontal bar chart of mean runtime per algorithm (log scale), whiskers = min to max."""
    means = [t[1] for t in runtimes]
    lows = [max(t[0], 1e-9) for t in runtimes]
    highs = [t[2] for t in runtimes]
    xerr = [
        [max(m - lo, 0.0) for m, lo in zip(means, lows)],
        [max(hi - m, 0.0) for m, hi in zip(means, highs)],
    ]

    fig, ax = plt.subplots(figsize=(10, 0.55 * len(labels) + 2))
    positions = _configure_hbar_axes(
        ax, labels, title,
        "Runtime in seconds (log scale) - bar = mean, whiskers = min to max",
    )
    ax.barh(positions, means, xerr=xerr, capsize=4, color=_COLOR_BLUE, ecolor="black")
    ax.set_xscale("log")
    ax.set_xlim(left=min(lows) / 5, right=max(highs) * 10)  # Headroom for the value labels

    _annotate_bars(
        ax, positions, highs,
        [format_duration(m, compact=True) for m in means],
        offset=6, fontsize=8,
    )
    return _save(fig, path)


def save_distance_bar_chart(
    path: Path,
    title: str,
    labels: Sequence[str],
    distances: Sequence[Triple],
    optimum: Optional[float] = None,
) -> Path:
    """Grouped horizontal bars of best / mean / worst tour distance per algorithm.

    The axis does not start at zero: otherwise differences of a few percent between
    algorithms would be invisible. Exact values are printed on the bars.
    """
    series = [
        ("Best (min)", 0, _COLOR_GREEN),
        ("Mean", 1, _COLOR_ORANGE),
        ("Worst (max)", 2, _COLOR_RED),
    ]
    height = 0.26
    all_values = [v for triple in distances for v in triple]
    lo, hi = min(all_values), max(all_values)

    fig, ax = plt.subplots(figsize=(10, 0.9 * len(labels) + 2))
    positions = _configure_hbar_axes(
        ax, labels, title,
        "Tour distance (axis does not start at zero) - lower is better",
    )
    for k, (name, idx, colour) in enumerate(series):
        offsets = [p + (k - 1) * height for p in positions]
        values = [triple[idx] for triple in distances]
        ax.barh(offsets, values, height, label=name, color=colour)
        _annotate_bars(
            ax, offsets, values,
            [f"{v:,.2f}" for v in values],
            offset=4, fontsize=7,
        )

    if optimum is not None:
        ax.axvline(
            optimum, linestyle="--", color=_COLOR_OPTIMUM,
            label=f"Proven optimum ({optimum:,.2f})",
        )
        lo = min(lo, optimum)

    ax.set_xlim(left=max(0.0, lo * 0.9), right=hi * 1.12)
    ax.legend(loc="lower right", fontsize=8)
    return _save(fig, path)


def save_scaling_line_chart(
    path: Path,
    title: str,
    ylabel: str,
    x_values: Sequence[int],
    series: Dict[str, List[Optional[float]]],
    log_y: bool = False,
) -> Path:
    """Line chart with one line per algorithm against number of cities.

    `series` maps an algorithm name to values aligned with `x_values` (None = not run).
    Algorithms with a single data point are drawn as a lone marker.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    for k, (name, values) in enumerate(series.items()):
        points = [(x, v) for x, v in zip(x_values, values) if v is not None]
        if not points:
            continue
        xs, ys = zip(*points)
        ax.plot(
            xs, ys, marker=_MARKERS[k % len(_MARKERS)], markersize=7, linewidth=1.8,
            color=plt.cm.tab10(k % 10), label=name,
        )

    if log_y:
        ax.set_yscale("log")
    ax.set_xticks(list(x_values))
    ax.set_xlabel("Number of cities")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=_GRID_ALPHA)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9)
    return _save(fig, path)


def _plot_convergence_panel(
    ax,
    panel_title: str,
    xlabel: str,
    traces: Sequence[Tuple[Sequence[float], Sequence[float], str, str, float, float, str]],
    optimum: Optional[float],
) -> None:
    """Render one convergence subplot (lines, optimum reference, and best-point markers)."""
    for xs, ys, colour, line_label, _, _, _ in traces:
        ax.plot(xs, ys, color=colour, linewidth=2, label=line_label)

    if optimum is not None:
        ax.axhline(
            optimum,
            color=_COLOR_GREEN,
            linestyle="--",
            linewidth=1.8,
            label=f"Proven Optimum ({optimum:.2f})",
        )

    for _, _, colour, _, conv_x, conv_y, point_label in traces:
        ax.scatter(
            [conv_x], [conv_y], color=colour, s=80, zorder=5,
            edgecolors="black", label=point_label,
        )

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel("Best Tour Distance", fontsize=10)
    ax.set_title(panel_title, fontsize=11, fontweight="bold")
    ax.grid(True, alpha=_GRID_ALPHA)
    ax.legend(fontsize=8, loc="upper right")


def save_convergence_chart(
    path: Path,
    title: str,
    sa_res: Dict,
    aco_res: Dict,
    optimum: Optional[float] = None,
) -> Path:
    """Renders and saves a dual-panel convergence chart:
    - Left panel: Best Tour Distance vs. Elapsed Wall-Clock Time (seconds).
    - Right panel: Best Tour Distance vs. Iteration Budget Progress (%).
    """
    fig, (ax_time, ax_prog) = plt.subplots(1, 2, figsize=(14, 5.5))

    algos = [
        ("Simulated Annealing", "SA", sa_res, _COLOR_BLUE),
        ("Ant Colony Opt.", "ACO", aco_res, _COLOR_ORANGE),
    ]

    time_traces = [
        (
            res["time_history"],
            res["history"],
            colour,
            f"{full_name} (best: {res['distance']:.2f})",
            res["conv_time_sec"],
            res["distance"],
            f"{short_name} Best @ {res['conv_time_sec']:.3f}s",
        )
        for full_name, short_name, res, colour in algos
    ]
    _plot_convergence_panel(
        ax_time,
        "Tour Distance vs. Elapsed Time (s)",
        "Elapsed Time (seconds)",
        time_traces,
        optimum,
    )

    prog_traces = []
    for _, short_name, res, colour in algos:
        n_hist = len(res["history"])
        prog_xs = [(i / n_hist) * 100 for i in range(1, n_hist + 1)]
        conv_pct = (res["convergence_iter"] / n_hist) * 100 if n_hist else 0.0
        prog_traces.append((
            prog_xs,
            res["history"],
            colour,
            f"{short_name} ({n_hist:,} iters)",
            conv_pct,
            res["distance"],
            f"{short_name} Best @ it {res['convergence_iter']:,} ({conv_pct:.1f}%)",
        ))
    _plot_convergence_panel(
        ax_prog,
        "Tour Distance vs. Budget Progress (%)",
        "Search Budget Completed (%)",
        prog_traces,
        optimum,
    )

    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return _save(fig, path)
