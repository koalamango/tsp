"""
Author: Jessie W

simulated_annealing_visualized.py - Animated visualizer for Simulated Annealing on TSP.

Inspired by jedrazb/python-tsp-simulated-annealing, adapted for this project's
80-city (and 10/20/40-city) Cartesian coordinate datasets.

Features:
  - Uses matplotlib.animation.FuncAnimation to animate tour evolution over iterations.
  - Supports both (City, X, Y) Cartesian sheets and symmetric distance matrices (with circular layout).
  - Side-by-side visualization:
      * Left panel: 2D map with current candidate route (exploring uphill moves at high T)
        and best-so-far route.
      * Right panels: Live tour distance learning curve (current vs. best) and
        temperature cooling curve.
  - Can display an interactive Matplotlib window and/or export directly to a GIF.

Usage:
    # Live visualization on the 80-city dataset (random initial route untangling)
    python algorithm/metaheuristics/simulated_annealing_visualized.py

    # Specify dataset, Nearest Neighbour start, or custom iteration count
    python algorithm/metaheuristics/simulated_annealing_visualized.py data/coordinates_80_cities.xlsx --nn-seed
    python algorithm/metaheuristics/simulated_annealing_visualized.py data/coordinates_80_cities.xlsx --iter 150000

    # Save animation to a GIF (e.g. for presentations or reports)
    python algorithm/metaheuristics/simulated_annealing_visualized.py data/coordinates_80_cities.xlsx --save-gif outputs/charts/sa_80_cities.gif
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, List, Optional, Tuple

import matplotlib
import numpy as np

# Preserve the system's interactive GUI backend before importing project modules
# (since tsp_charts.py sets matplotlib.use("Agg") for headless batch reports).
_INTERACTIVE_BACKEND = matplotlib.get_backend()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from algorithm.metaheuristics.metaheuristic import (
    SAFrame,
    solve_tsp_sa,
)
from utils.tsp_data import load_coordinates_or_matrix

# Restore interactive backend after tsp_charts import
matplotlib.use(_INTERACTIVE_BACKEND)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402


DEFAULT_DATASET = "data/coordinates_80_cities.xlsx"


def run_sa_with_snapshots(
    dist_matrix: List[List[float]],
    max_iter: int = 80000,
    t_init: Optional[float] = None,
    alpha: Optional[float] = None,
    use_nn_seed: bool = False,
    seed: int = 42,
    max_frames: int = 250,
) -> Tuple[List[SAFrame], List[float], List[float], List[float]]:
    """Run Simulated Annealing and capture tour snapshots for FuncAnimation.

    Compatibility wrapper delegating to the unified solve_tsp_sa in metaheuristic.py.

    Returns:
        frames: Sampled list of SAFrame objects for animation.
        best_history: Best distance at every iteration (including iter 0).
        curr_history: Current distance at every iteration (including iter 0).
        temp_history: Temperature at every iteration (including iter 0).
    """
    res = solve_tsp_sa(
        dist_matrix=dist_matrix,
        t_init=t_init,
        alpha=alpha,
        max_iter=max_iter,
        seed=seed,
        use_nn_seed=use_nn_seed,
        record_snapshots=True,
        max_frames=max_frames,
    )
    initial_dist = res["initial_distance"]
    initial_temp = res["frames"][0].temperature if res.get("frames") else (t_init or 30.0)
    best_history = [initial_dist] + res["history"]
    curr_history = [initial_dist] + res["curr_history"]
    temp_history = [initial_temp] + res["temp_history"]
    return res["frames"], best_history, curr_history, temp_history


@dataclass
class MapArtists:
    curr_line: Any
    best_line: Any
    telemetry_box: Any
    ax_map: Any


@dataclass
class CostArtists:
    curr_line: Any
    best_line: Any
    marker: Any


@dataclass
class TemperatureArtists:
    line: Any
    marker: Any


def create_figure_layout():
    """Sets up the overall layout of the animation"""
    fig = plt.figure(figsize=(14, 7.5), facecolor="#F8F9FA")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1.0], height_ratios=[1.3, 1.0], hspace=0.32, wspace=0.22)
    ax_map = fig.add_subplot(gs[:, 0])
    ax_cost = fig.add_subplot(gs[0, 1])
    ax_temp = fig.add_subplot(gs[1, 1])
    return fig, ax_map, ax_cost, ax_temp


def build_map_panel(
    ax_map,
    cities: List[str],
    points: List[Tuple[float, float]],
    xlabel: str,
    ylabel: str,
    show_labels: bool,
) -> MapArtists:
    """Sets up the graph for rendering the map and route for the current iteration"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n_cities = len(cities)
    pad_x = (max(xs) - min(xs)) * 0.07 or 10.0
    pad_y = (max(ys) - min(ys)) * 0.07 or 10.0

    ax_map.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
    ax_map.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
    ax_map.set_aspect("equal", adjustable="datalim")
    ax_map.set_xlabel(xlabel)
    ax_map.set_ylabel(ylabel)
    ax_map.grid(True, linestyle="--", alpha=0.3)

    curr_line, = ax_map.plot(
        [], [], color="#F28E2B", linestyle="--", linewidth=1.1, alpha=0.55,
        label="Current Candidate Route", zorder=2,
    )
    best_line, = ax_map.plot(
        [], [], color="#1F77B4", linestyle="-", linewidth=2.2, alpha=0.95,
        label="Best Route So Far", zorder=3,
    )

    ax_map.scatter(
        xs[1:], ys[1:], s=36, color="#2C3E50", edgecolors="white", linewidth=0.6,
        zorder=4, label=f"Cities ({n_cities})",
    )
    ax_map.scatter(
        [xs[0]], [ys[0]], s=120, color="#E15759", marker="*", edgecolors="black",
        linewidth=0.8, zorder=5, label=f"Start/Finish ({cities[0]})",
    )

    if show_labels or n_cities <= 25:
        for name, (x, y) in zip(cities, points):
            ax_map.annotate(
                name, (x, y), xytext=(4, 3), textcoords="offset points",
                fontsize=7.5, color="#222222", zorder=6,
            )
    else:
        ax_map.annotate(
            cities[0], (xs[0], ys[0]), xytext=(6, 4), textcoords="offset points",
            fontsize=8.5, fontweight="bold", color="#B01A1C", zorder=6,
        )

    ax_map.legend(loc="upper left", fontsize=8.5, framealpha=0.9)

    telemetry_box = ax_map.text(
        0.02, 0.02, "", transform=ax_map.transAxes, fontsize=9,
        verticalalignment="bottom", family="monospace",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#CCCCCC", alpha=0.92),
        zorder=7,
    )
    return MapArtists(curr_line=curr_line, best_line=best_line, telemetry_box=telemetry_box, ax_map=ax_map)


def build_cost_panel(
    ax_cost,
    best_history: List[float],
    curr_history: List[float],
    max_iter: int,
) -> CostArtists:
    """Sets up the graph for rendering the distance found"""
    iters_all = np.arange(len(best_history))
    ax_cost.plot(iters_all, curr_history, color="#F28E2B", alpha=0.12, linewidth=0.7)
    ax_cost.set_xlim(0, max(1, max_iter))
    ax_cost.set_ylim(min(best_history) * 0.92, max(curr_history) * 1.04)
    ax_cost.set_title("Tour Distance vs. Iteration", fontsize=11, fontweight="bold")
    ax_cost.set_ylabel("Tour Distance")
    ax_cost.grid(True, linestyle="--", alpha=0.3)

    curr_line, = ax_cost.plot([], [], color="#F28E2B", alpha=0.6, linewidth=1.0, label="Current Distance")
    best_line, = ax_cost.plot([], [], color="#1F77B4", linewidth=2.0, label="Best Distance")
    marker, = ax_cost.plot([], [], "o", color="#E15759", markersize=6, zorder=5)
    ax_cost.legend(loc="upper right", fontsize=8.5)
    return CostArtists(curr_line=curr_line, best_line=best_line, marker=marker)


def build_temperature_panel(
    ax_temp,
    temp_history: List[float],
    max_iter: int,
) -> TemperatureArtists:
    """Sets up the temperature graph"""
    iters_all = np.arange(len(temp_history))
    ax_temp.plot(iters_all, temp_history, color="#E15759", alpha=0.2, linewidth=1.0)
    ax_temp.set_xlim(0, max(1, max_iter))
    ax_temp.set_ylim(0, max(temp_history) * 1.06)
    ax_temp.set_title("Annealing Temperature Schedule (T)", fontsize=11, fontweight="bold")
    ax_temp.set_xlabel("Iteration")
    ax_temp.set_ylabel("Temperature (T)")
    ax_temp.grid(True, linestyle="--", alpha=0.3)

    temp_line, = ax_temp.plot([], [], color="#E15759", linewidth=2.0, label="Temperature T")
    marker, = ax_temp.plot([], [], "o", color="#E15759", markersize=6, zorder=5)
    ax_temp.legend(loc="upper right", fontsize=8.5)
    return TemperatureArtists(line=temp_line, marker=marker)


def create_frame_updater(
    frames: List[SAFrame],
    points: List[Tuple[float, float]],
    best_history: List[float],
    curr_history: List[float],
    temp_history: List[float],
    map_artists: MapArtists,
    cost_artists: CostArtists,
    temp_artists: TemperatureArtists,
):
    """Implements and returns a function that renders the next frame in the animation"""
    n_cities = len(points)
    max_iter = len(best_history) - 1
    initial_dist = frames[0].curr_dist
    iters_all = np.arange(len(best_history))
    plot_step = max(1, max_iter // 1000)

    def update(frame_idx: int):
        frame = frames[frame_idx]
        it = frame.iteration

        curr_xs = [points[idx][0] for idx in frame.curr_route]
        curr_ys = [points[idx][1] for idx in frame.curr_route]
        map_artists.curr_line.set_data(curr_xs, curr_ys)

        best_xs = [points[idx][0] for idx in frame.best_route]
        best_ys = [points[idx][1] for idx in frame.best_route]
        map_artists.best_line.set_data(best_xs, best_ys)

        map_artists.curr_line.set_alpha(0.0 if frame_idx == len(frames) - 1 else 0.55)

        sliced_iters = iters_all[: it + 1 : plot_step]
        cost_artists.curr_line.set_data(sliced_iters, curr_history[: it + 1 : plot_step])
        cost_artists.best_line.set_data(sliced_iters, best_history[: it + 1 : plot_step])
        cost_artists.marker.set_data([it], [frame.best_dist])

        temp_artists.line.set_data(sliced_iters, temp_history[: it + 1 : plot_step])
        temp_artists.marker.set_data([it], [frame.temperature])

        improvement_pct = (1.0 - frame.best_dist / initial_dist) * 100.0 if initial_dist > 0 else 0.0
        map_artists.ax_map.set_title(
            f"Simulated Annealing TSP ({n_cities} Cities) — Best Distance: {frame.best_dist:,.2f}",
            fontsize=12, fontweight="bold",
        )
        map_artists.telemetry_box.set_text(
            f"Iteration   : {it:>9,d} / {max_iter:,d}\n"
            f"Temperature : {frame.temperature:>9.3f}\n"
            f"Current Dist: {frame.curr_dist:>9,.2f}\n"
            f"Best Dist   : {frame.best_dist:>9,.2f} (-{improvement_pct:.1f}%)\n"
            f"Improvements: {frame.improved_moves:>9,d}"
        )
        return (
            map_artists.curr_line, map_artists.best_line,
            cost_artists.curr_line, cost_artists.best_line, cost_artists.marker,
            temp_artists.line, temp_artists.marker, map_artists.telemetry_box,
        )

    return update


def save_or_show_animation(
    anim: FuncAnimation,
    fig,
    save_gif: Optional[str],
    show_window: bool,
    interval_ms: int,
    frame_count: int,
) -> None:
    """Renders the created image or saves it to disk"""
    if save_gif:
        out_path = Path(save_gif)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fps = max(1, int(1000 / max(interval_ms, 10)))
        print(f"Saving animation ({frame_count} frames at {fps} FPS) to {out_path} ...", flush=True)
        anim.save(str(out_path), writer=PillowWriter(fps=fps))
        print(f"Saved GIF to: {out_path}", flush=True)

    if show_window:
        plt.show()
    else:
        plt.close(fig)


def animate_simulated_annealing(
    cities: List[str],
    points: List[Tuple[float, float]],
    frames: List[SAFrame],
    best_history: List[float],
    curr_history: List[float],
    temp_history: List[float],
    xlabel: str = "X Coordinate",
    ylabel: str = "Y Coordinate",
    interval_ms: int = 35,
    show_labels: bool = False,
    save_gif: Optional[str] = None,
    show_window: bool = True,
) -> FuncAnimation:
    """Create and run the Matplotlib FuncAnimation for Simulated Annealing."""
    max_iter = len(best_history) - 1

    fig, ax_map, ax_cost, ax_temp = create_figure_layout()
    map_artists = build_map_panel(ax_map, cities, points, xlabel, ylabel, show_labels)
    cost_artists = build_cost_panel(ax_cost, best_history, curr_history, max_iter)
    temp_artists = build_temperature_panel(ax_temp, temp_history, max_iter)

    update = create_frame_updater(
        frames, points, best_history, curr_history, temp_history,
        map_artists, cost_artists, temp_artists,
    )

    anim = FuncAnimation(
        fig,
        update,
        frames=len(frames),
        interval=interval_ms,
        blit=False,
        repeat=False,
    )

    save_or_show_animation(anim, fig, save_gif, show_window, interval_ms, len(frames))
    return anim


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Visualize Simulated Annealing on 80-city (or custom) TSP datasets."
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=DEFAULT_DATASET,
        help=f"Path to Excel dataset (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--iter",
        type=int,
        default=None,
        help="Number of SA iterations (default: auto-scaled max(20000, 15 * n^2))",
    )
    parser.add_argument(
        "--nn-seed",
        action="store_true",
        help="Start from Nearest Neighbour greedy tour instead of a random tour",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=250,
        help="Number of animation frames to display/export (default: 250)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=35,
        help="Delay between frames in milliseconds (default: 35)",
    )
    parser.add_argument(
        "--labels",
        action="store_true",
        help="Show all city name labels on the map (even for > 25 cities)",
    )
    parser.add_argument(
        "--save-gif",
        nargs="?",
        const="AUTO",
        default=None,
        help="Export animation as a .gif file (defaults to outputs/charts/<dataset>_sa.gif if no path given)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open an interactive GUI window even when --save-gif is specified",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not open an interactive window",
    )
    args = parser.parse_args(argv)

    save_gif_path = args.save_gif
    if save_gif_path == "AUTO":
        stem = Path(args.file).stem
        suffix = "nn" if args.nn_seed else "random"
        save_gif_path = f"outputs/charts/{stem}_sa_{suffix}.gif"

    if args.no_show:
        show_window = False
    elif args.show:
        show_window = True
    else:
        # By default, open GUI window only if not saving to GIF
        show_window = (save_gif_path is None)

    cities, points, dist_matrix, xlabel, ylabel = load_coordinates_or_matrix(args.file)
    n_cities = len(cities)
    max_iter = args.iter if args.iter is not None else max(20000, 15 * n_cities * n_cities)

    start_mode = "Nearest Neighbour Tour" if args.nn_seed else "Random Tour"
    print(f"Dataset       : {args.file} ({n_cities} cities)", flush=True)
    print(f"Initial Route : {start_mode}", flush=True)
    print(f"SA Iterations : {max_iter:,} (seed={args.seed})", flush=True)

    frames, best_hist, curr_hist, temp_hist = run_sa_with_snapshots(
        dist_matrix,
        max_iter=max_iter,
        use_nn_seed=args.nn_seed,
        seed=args.seed,
        max_frames=args.frames,
    )

    initial_d = frames[0].curr_dist
    final_d = frames[-1].best_dist
    reduction = (1.0 - final_d / initial_d) * 100.0 if initial_d > 0 else 0.0
    print(f"Initial Dist  : {initial_d:,.2f}", flush=True)
    print(f"Final Best    : {final_d:,.2f} (-{reduction:.1f}% reduction, {frames[-1].improved_moves} improvements)", flush=True)

    animate_simulated_annealing(
        cities=cities,
        points=points,
        frames=frames,
        best_history=best_hist,
        curr_history=curr_hist,
        temp_history=temp_hist,
        xlabel=xlabel,
        ylabel=ylabel,
        interval_ms=args.interval,
        show_labels=args.labels,
        save_gif=save_gif_path,
        show_window=show_window,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
