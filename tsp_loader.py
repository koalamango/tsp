"""
Author: Jessie W

tsp_loader.py - Unified orchestrator for Travelling Salesperson Problem algorithms.

Runs each implemented TSP algorithm in turn across available datasets:
  1. Exact MILP Solver (HiGHS via scipy.optimize.milp with DFJ subtour elimination)
  2. Nearest Neighbour (Greedy constructive heuristic)
  3. 2-Opt Local Search (Edge-reversal iterative refinement)
  4. 3-Opt Local Search (7-case triplet reconnection iterative refinement)
  5. Simulated Annealing (Metaheuristic: hybrid 2-opt + swap)
  6. Ant Colony Optimization (Metaheuristic: Ant System)
  7. Exact Solvers: Brute Force & Dynamic Programming (Held-Karp)

Every algorithm is run several times per dataset (default 10, see --runs). Runtime
statistics (min / mean / max / SD) are recorded for every algorithm; distance
statistics are recorded for the non-deterministic ones (Simulated Annealing and Ant
Colony Optimization), which use a different seed (--seed + run index) on every run.

Each dataset report embeds two bar charts (runtime; best/mean/worst distance). When two or
more datasets of different sizes are run, a scalability summary with line graphs of runtime
and best-result gap against number of cities is also written. Charts are saved as PNGs in
outputs/charts/.

Usage:
  python tsp_loader.py
  python tsp_loader.py --runs 25 --seed 7
  python tsp_loader.py --no-exact
  python tsp_loader.py --help
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import itertools
import math
import random
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# Third-party imports
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Project modules
from algorithm.heuristics.nearest_neighbour import (
    exact_route,
    nearest_neighbour,
    route_length,
)
from utils.tsp_data import (
    build_euclidean_matrix,
    load_tsp_data,
    read_cities,
)
from algorithm.heuristics.two_opt import two_opt
from algorithm.heuristics.three_opt import three_opt
from algorithm.metaheuristics.metaheuristic import (
    SA_ACCEPT_PROB,
    SA_CALIBRATION_SAMPLES,
    SA_FINAL_TEMP_RATIO,
    SA_ITER_FACTOR,
    SA_MIN_ITER,
    SAParams,
    calibrate_initial_temperature,
    sa_parameters_for,
    solve_tsp_sa,
    solve_tsp_aco,
)
from algorithm.exact.dynamic_programming.held_karp import run_held_karp
from utils.tsp_charts import (
    save_distance_bar_chart,
    save_runtime_bar_chart,
    save_scaling_line_chart,
)
from utils.tsp_utils import (
    format_duration,
    format_gap,
    format_route,
    markdown_table,
    pluralize,
)

DEFAULT_RUNS = 10
DEFAULT_SEED = 42

EXACT_ALGORITHM = "Exact MILP (HiGHS)"
CHARTS_DIRNAME = "charts"  # Sub-folder of outputs/ holding the PNG charts linked from the reports

# Default Cartesian datasets evaluated in sequence: (filepath, run_exact_solvers)
CARTESIAN_SUITES: List[Tuple[str, bool]] = [
    ("data/coordinates_10_cities.xlsx", True),
    ("data/coordinates_20_cities.xlsx", False),
    ("data/coordinates_40_cities.xlsx", False),
    ("data/coordinates_80_cities.xlsx", False),
]

# A stochastic run "hits the optimum" when it is within this distance of the MILP optimum.
OPT_TOLERANCE = 1e-6

NN_FOOTNOTE = (
    "† Time includes building the Nearest Neighbour starting tour (2-Opt and 3-Opt cannot "
    "run without it), i.e. NN time + refinement time."
)


def estimate_exact_times(n: int) -> Tuple[str, str, int]:
    """Calculate theoretical operations and estimated runtimes for Brute Force & Dynamic Programming (Held-Karp)."""
    perms = math.factorial(n - 1)
    # Calibrated Python throughput: ~1,000,000 permutations/sec
    bf_seconds = perms / 1_000_000.0

    # Held-Karp dynamic programming transitions: O(n^2 * 2^n)
    # Calibrated Python throughput: ~2,000,000 state transitions/sec
    hk_ops = (n ** 2) * (1 << n)
    hk_seconds = hk_ops / 2_000_000.0

    return format_duration(bf_seconds), format_duration(hk_seconds), perms


def run_brute_force(dist_matrix: List[List[float]], start: int = 0) -> List[int]:
    """Exhaustive brute-force permutation search (matching algorithm/exact/brute_force/brute_force.py logic)."""
    n = len(dist_matrix)
    if n <= 1:
        return [0, 0] if n == 1 else []

    other_cities = [i for i in range(n) if i != start]
    best_route = None
    min_distance = float("inf")

    for perm in itertools.permutations(other_cities):
        current_route = [start] + list(perm) + [start]
        current_distance = 0.0
        for i in range(n):
            current_distance += dist_matrix[current_route[i]][current_route[i + 1]]
        if current_distance < min_distance:
            min_distance = current_distance
            best_route = current_route

    return best_route if best_route is not None else [start, start]


def slugify(text: str) -> str:
    """Convert a suite title into a safe filename slug."""
    slug = re.sub(r"[^a-z0-9\-_]+", "_", text.lower())
    return re.sub(r"_+", "_", slug).strip("_")


@dataclass(frozen=True)
class Stats:
    """Min / mean / max / sample standard deviation of a series of measurements."""
    min: float
    mean: float
    max: float
    sd: float

    @property
    def triple(self) -> Tuple[float, float, float]:
        return self.min, self.mean, self.max

    @classmethod
    def from_values(cls, values: Sequence[float]) -> "Stats":
        sd = statistics.stdev(values) if len(values) > 1 else 0.0
        return cls(min(values), statistics.fmean(values), max(values), sd)


@dataclass
class RunRecord:
    """A single timed execution of one algorithm."""
    route: List[int]
    distance: float
    time_sec: float
    seed: Optional[int] = None
    extra_info: Optional[str] = None


@dataclass
class BenchmarkResult:
    """All timed runs of one TSP algorithm on one dataset, plus summary statistics."""
    algorithm: str
    deterministic: bool
    runs: List[RunRecord]
    gap_str: str  # Gap of the best run vs the optimum
    opt_distance: Optional[float] = None
    includes_nn_time: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.algorithm} †" if self.includes_nn_time else self.algorithm

    @property
    def series_name(self) -> str:
        """Algorithm name without a trailing '(N cities)', so it is stable across datasets."""
        return re.sub(r"\s*\(\d+ cities\)$", "", self.algorithm)

    @property
    def best_run(self) -> RunRecord:
        return min(self.runs, key=lambda r: r.distance)

    @property
    def distance(self) -> float:
        """Distance of the best run."""
        return self.best_run.distance

    @property
    def time_stats(self) -> Stats:
        return Stats.from_values([r.time_sec for r in self.runs])

    @property
    def distance_stats(self) -> Stats:
        return Stats.from_values([r.distance for r in self.runs])

    def optimum_hit_rate(self) -> str:
        """Runs that reached the proven optimum, e.g. '7/10' ('N/A' without an exact baseline)."""
        if self.opt_distance is None:
            return "N/A"
        hits = sum(1 for r in self.runs if r.distance <= self.opt_distance + OPT_TOLERANCE)
        return f"{hits}/{len(self.runs)}"

    def to_summary_row(self, cities: List[str]) -> List[str]:
        return [
            self.display_name,
            f"{self.distance:,.2f}",
            f"{self.time_stats.mean:.6f}",
            self.gap_str,
            format_route(self.best_run.route, cities),
        ]

    def to_runtime_row(self) -> List[str]:
        s = self.time_stats
        return [self.display_name, f"{s.min:.6f}", f"{s.mean:.6f}", f"{s.max:.6f}", f"{s.sd:.6f}"]

    def to_distance_row(self) -> List[str]:
        s = self.distance_stats
        return [
            self.display_name,
            f"{s.min:,.2f}",
            f"{s.mean:,.2f}",
            f"{s.max:,.2f}",
            f"{s.sd:,.2f}",
            format_gap(s.mean, self.opt_distance),
            self.optimum_hit_rate(),
        ]

    def to_detail_markdown(self, cities: List[str]) -> str:
        t = self.time_stats
        itinerary = format_route(self.best_run.route, cities, max_display=None)
        runs_label = pluralize(len(self.runs))
        lines = [
            f"### {self.display_name}",
            f"- **Final Distance{'' if self.deterministic else ' (best run)'}:** {self.distance:,.2f}",
            f"- **Runtime:** {t.mean:.6f} ± {t.sd:.6f} seconds "
            f"(mean ± SD over {runs_label}; min {t.min:.6f}, max {t.max:.6f})",
        ]
        if not self.deterministic:
            d = self.distance_stats
            lines.append(
                f"- **Distance over {runs_label}:** min {d.min:,.2f} / mean {d.mean:,.2f} / "
                f"max {d.max:,.2f} (SD {d.sd:,.2f})"
            )
        lines.append(f"- **Full Tour Itinerary{'' if self.deterministic else ' (best run)'}:**")
        lines.append(f"  `{itinerary}`\n")
        return "\n".join(lines)


@dataclass
class SuiteSummary:
    """Results of one dataset, kept so cross-dataset charts can be built after all runs."""
    suite_name: str
    n_cities: int
    results: List[BenchmarkResult]
    slug: str = ""






def run_benchmarks(
    cities: List[str],
    dist_matrix: List[List[float]],
    run_exact: bool = True,
    run_exact_solvers: bool = True,
    runs: int = DEFAULT_RUNS,
    seed: int = DEFAULT_SEED,
    sa_params: Optional[SAParams] = None,
) -> List[BenchmarkResult]:
    """Run all configured TSP algorithms `runs` times each and return their benchmark results."""
    n = len(cities)
    results: List[BenchmarkResult] = []
    opt_distance: Optional[float] = None
    sa_cfg = SAParams.from_config(sa_params) if sa_params is not None else sa_parameters_for(dist_matrix, seed)

    # A solver takes the 0-based run index (-1 for the warm-up) and returns (route, extra info).
    Solver = Callable[[int], Tuple[List[int], Optional[str]]]

    def run_step(
        step_label: str,
        algo_name: str,
        solver_fn: Solver,
        deterministic: bool = True,
        includes_nn_time: bool = False,
        gap_override: Optional[str] = None,
        gap_default: str = "N/A",
    ) -> BenchmarkResult:
        """Announce, warm up, time `runs` executions, evaluate, and record a TSP solver."""
        sys.stdout.write(f"  {step_label} ")
        sys.stdout.flush()

        # Warm-up run (untimed, result discarded). The very first call of a solver pays
        # one-off costs - lazy imports/initialisation (e.g. HiGHS/scipy setup), cold CPU
        # caches, memory allocation and CPU frequency ramp-up. Left in, they would inflate
        # the first measurement and therefore the reported maximum runtime and SD, making
        # the statistics reflect start-up cost rather than the algorithm itself.
        solver_fn(-1)

        records: List[RunRecord] = []
        for run_idx in range(runs):
            t0 = time.perf_counter()
            route, extra_info = solver_fn(run_idx)
            elapsed = time.perf_counter() - t0  # Only the solver is timed, not route evaluation

            records.append(RunRecord(
                route=route,
                distance=route_length(route, dist_matrix),
                time_sec=elapsed,
                seed=None if deterministic else seed + run_idx,
                extra_info=extra_info,
            ))
            sys.stdout.write(".")
            sys.stdout.flush()

        best = min(records, key=lambda r: r.distance)
        gap = (
            gap_override if gap_override is not None
            else format_gap(best.distance, opt_distance, default=gap_default)
        )
        res = BenchmarkResult(
            algorithm=algo_name,
            deterministic=deterministic,
            runs=records,
            gap_str=gap,
            opt_distance=opt_distance,
            includes_nn_time=includes_nn_time,
        )

        t, d = res.time_stats, res.distance_stats
        detail_parts = [f"best {best.distance:,.2f}", gap, f"{t.mean:.4f}s +/- {t.sd:.4f}s"]
        if not deterministic:
            detail_parts.append(f"mean dist {d.mean:,.2f}")
            detail_parts.append(f"optimum hit {res.optimum_hit_rate()}")
        if best.extra_info:
            detail_parts.append(best.extra_info)
        print(f" done ({' | '.join(detail_parts)})")

        if deterministic and d.max - d.min > OPT_TOLERANCE:
            print(
                f"  WARNING: {algo_name} is expected to be deterministic but its distance "
                f"varied across runs ({d.min:,.4f} - {d.max:,.4f})."
            )

        results.append(res)
        return res

    # 1. Exact MILP Reference (HiGHS)
    if run_exact:
        try:
            exact_res = run_step(
                f"[1/6] {EXACT_ALGORITHM}",
                EXACT_ALGORITHM,
                lambda _i: (exact_route(dist_matrix), None),
                gap_override="0.00% (proven)",
            )
            opt_distance = exact_res.distance
        except Exception as e:
            print(f"failed ({e})")

    # 2. Nearest Neighbour
    run_step(
        "[2/6] Nearest Neighbour",
        "Nearest Neighbour",
        lambda _i: (nearest_neighbour(dist_matrix)[0], None),
    )

    # 3–6. Local Search Refinements & Stochastic Metaheuristics
    def solve_from_nn(fn: Callable) -> Solver:
        """2-Opt/3-Opt need a Nearest Neighbour tour, so every timed run builds it first."""
        def solve(_run_idx: int) -> Tuple[List[int], str]:
            nn_route, _ = nearest_neighbour(dist_matrix)
            tour, _, _, moves = fn(nn_route, dist_matrix)
            return tour, f"{moves} moves"
        return solve

    def solve_metaheuristic(fn: Callable, **kwargs) -> Solver:
        """Each run gets its own reproducible seed: base seed + run index."""
        def solve(run_idx: int) -> Tuple[List[int], None]:
            res = fn(dist_matrix, seed=seed + run_idx, **kwargs)
            return res["route"], None
        return solve

    # (step label, algorithm name, solver, deterministic, time includes NN construction)
    heuristic_steps = [
        ("[3/6] 2-Opt Refinement", "2-Opt (from NN)", solve_from_nn(two_opt), True, True),
        ("[4/6] 3-Opt Refinement", "3-Opt (from NN)", solve_from_nn(three_opt), True, True),
        ("[5/6] Simulated Annealing", "Simulated Annealing",
         solve_metaheuristic(
             solve_tsp_sa,
             t_init=sa_cfg.t_init,
             alpha=sa_cfg.alpha,
             max_iter=sa_cfg.max_iter,
             record_history=False,
         ),
         False, False),
        ("[6/6] Ant Colony Optimization", "Ant Colony Opt.",
         solve_metaheuristic(solve_tsp_aco, n_ants=20, n_iter=150), False, False),
    ]
    for step_label, algo_name, solver_fn, deterministic, includes_nn in heuristic_steps:
        run_step(step_label, algo_name, solver_fn,
                 deterministic=deterministic, includes_nn_time=includes_nn)

    # Optional: Exact Solvers under algorithm/exact (Brute Force & Dynamic Programming)
    if run_exact_solvers:
        bonus_steps = [
            (
                f"[Bonus] Brute Force ({math.factorial(n - 1):,} permutations)",
                f"Brute Force ({n} cities)",
                lambda _i: (run_brute_force(dist_matrix), None),
            ),
            (
                f"[Bonus] Dynamic Programming (Held-Karp)",
                f"Held-Karp DP ({n} cities)",
                lambda _i: (run_held_karp(cities, dist_matrix)["route"], f"{n * (1 << n):,} states"),
            ),
        ]
        for step_label, algo_name, solver_fn in bonus_steps:
            run_step(step_label, algo_name, solver_fn, gap_default="0.00%")

    return results


def write_runs_csv(
    suite_name: str,
    results: List[BenchmarkResult],
    outputs_dir: Path = Path("outputs"),
    slug: Optional[str] = None,
) -> Path:
    """Export every timed run (warm-ups excluded) to CSV for analysis in Excel / pandas."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "algorithm": res.algorithm,
            "deterministic": res.deterministic,
            "run": run_no,
            "seed": rec.seed,
            "distance": rec.distance,
            "time_sec": rec.time_sec,
        }
        for res in results
        for run_no, rec in enumerate(res.runs, start=1)
    ]
    df = pd.DataFrame(rows)
    df["seed"] = df["seed"].astype("Int64")  # Blank (not 42.0) for deterministic algorithms
    safe_name = slugify(slug if slug else suite_name)
    csv_file = outputs_dir / f"tsp_loader_{safe_name}_runs.csv"
    df.to_csv(csv_file, index=False)
    return csv_file


def find_optimum(results: List[BenchmarkResult]) -> Optional[float]:
    """Proven optimal distance from the exact MILP run, or None if it was skipped/failed."""
    exact = next((r for r in results if r.algorithm == EXACT_ALGORITHM), None)
    return exact.distance if exact else None


def write_suite_charts(
    suite_name: str,
    cities: List[str],
    results: List[BenchmarkResult],
    outputs_dir: Path = Path("outputs"),
    slug: Optional[str] = None,
) -> Tuple[Path, Path]:
    """Render the runtime and best/mean/worst-distance bar charts for one dataset."""
    charts_dir = outputs_dir / CHARTS_DIRNAME
    safe_name = slugify(slug if slug else suite_name)
    n, runs = len(cities), len(results[0].runs)
    runs_label = pluralize(runs)
    labels = [r.display_name for r in results]

    runtime_png = save_runtime_bar_chart(
        charts_dir / f"tsp_loader_{safe_name}_runtime.png",
        f"Runtime per algorithm - {n} cities, {runs_label}",
        labels,
        [r.time_stats.triple for r in results],
    )
    distance_png = save_distance_bar_chart(
        charts_dir / f"tsp_loader_{safe_name}_distance.png",
        f"Tour distance per algorithm - {n} cities, {runs_label}",
        labels,
        [r.distance_stats.triple for r in results],
        optimum=find_optimum(results),
    )
    return runtime_png, distance_png


def write_markdown_report(
    suite_name: str,
    cities: List[str],
    results: List[BenchmarkResult],
    runs: int = DEFAULT_RUNS,
    seed: int = DEFAULT_SEED,
    sa_params: Optional[SAParams] = None,
    outputs_dir: Path = Path("outputs"),
    slug: Optional[str] = None,
) -> Path:
    """Format benchmark results into a Markdown report and save to disk."""
    n = len(cities)
    runs_label = pluralize(runs)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(slug if slug else suite_name)
    any_nn_footnote = any(r.includes_nn_time for r in results)
    footnote_lines = ["", NN_FOOTNOTE] if any_nn_footnote else []

    summary_table = markdown_table(
        ["Algorithm", "Distance (best run)", "Mean Time (s)", "Gap vs Opt", "Route Summary"],
        [r.to_summary_row(cities) for r in results],
    )

    runtime_table = markdown_table(
        ["Algorithm", "Min (s)", "Mean (s)", "Max (s)", "SD (s)"],
        [r.to_runtime_row() for r in results],
    )

    stochastic = [r for r in results if not r.deterministic]
    distance_lines: List[str] = []
    if stochastic:
        distance_table = markdown_table(
            ["Algorithm", "Min", "Mean", "Max", "SD", "Mean Gap vs Opt", "Optimum Hit Rate"],
            [r.to_distance_row() for r in stochastic],
        )
        distance_lines = [
            "## Distance Statistics (Non-Deterministic Algorithms)",
            "",
            f"Final tour distance over {runs_label}, each with a different seed. "
            "*Optimum Hit Rate* is the number of runs that reached the proven optimum "
            "(N/A when the exact solver was skipped).",
            "",
            distance_table,
            "",
        ]

    detail_lines = [res.to_detail_markdown(cities) for res in results]

    # Scalability / runtime estimation section (especially pertinent for n > 10)
    scalability_lines = []
    if n > 10:
        bf_est, hk_est, perms = estimate_exact_times(n)
        exact_res = next((r for r in results if r.algorithm == EXACT_ALGORITHM), None)
        highs_time_str = (
            f"**{exact_res.time_stats.mean:.4f} seconds** (actual, mean of {runs_label})"
            if exact_res else "Skipped"
        )
        hk_status = "Solved to global optimum" if n <= 10 else ("Feasible exact solver" if n <= 16 else "Exponential compute / memory limit")
        scalability_table = markdown_table(
            ["Exact Method", "Theoretical Operations / States", "Estimated Runtime on this Machine", "Status"],
            [
                ["**Pure Brute Force**", f"$(n-1)! = {perms:,}$ permutations", f"**{bf_est}**", "Infeasible for real-time run" if n > 10 else "Solved to global optimum"],
                ["**Held-Karp DP**", f"$O(n^2 2^n) \\approx {(n**2)*(1 << n):,}$ operations", f"**{hk_est}**", hk_status],
                ["**HiGHS MILP Solver**", "Dynamic DFJ subtour cuts", highs_time_str, "Solved to global optimum"],
            ],
        )
        scalability_lines = [
            "## Exact Scalability Projections for this Dataset",
            "",
            f"Because this dataset has **{n} cities**, exhaustive exact methods grow factorially / exponentially:",
            "",
            scalability_table,
            "",
            "> [!NOTE]",
            "> Estimates are calibrated against your CPU's measured throughput (~1,000,000 permutations/second).",
            "",
        ]

    sa_line = []
    if sa_params:
        sa_cfg = SAParams.from_config(sa_params)
        sa_line = [
            f"- **Simulated Annealing parameters:** t_init={sa_cfg.t_init:.2f}, "
            f"alpha={sa_cfg.alpha:.6f}, max_iter={int(sa_cfg.max_iter):,} (scaled to n = {n})"
        ]

    runtime_png, distance_png = write_suite_charts(
        suite_name, cities, results, outputs_dir, slug=safe_name
    )
    chart_lines = [
        "## Charts",
        "",
        "### Runtime per Algorithm",
        "",
        f"![Runtime per algorithm: mean with min-max whiskers, log scale]({CHARTS_DIRNAME}/{runtime_png.name})",
        "",
        "### Tour Distance per Algorithm (Best / Mean / Worst)",
        "",
        f"![Best, mean and worst tour distance per algorithm]({CHARTS_DIRNAME}/{distance_png.name})",
        "",
        "Deterministic algorithms return the same tour every run, so their best, mean and worst bars are identical.",
        *footnote_lines,
        "",
    ]

    md_lines = [
        f"# TSP Benchmark Results: {suite_name}",
        "",
        f"- **Cities Evaluated:** {n} ({', '.join(cities)})",
        f"- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Runs per algorithm:** {runs} (plus 1 untimed warm-up run each)",
        f"- **Base seed:** {seed} (Simulated Annealing / Ant Colony run *i* uses seed + *i*)",
        *sa_line,
        "",
        "## Performance & Quality Summary",
        "",
        "Distance and gap are from the **best run**; time is the **mean** over all runs.",
        "",
        summary_table,
        *footnote_lines,
        "",
        "## Runtime Statistics (All Algorithms)",
        "",
        runtime_table,
        *footnote_lines,
        "",
        *distance_lines,
        *chart_lines,
        *scalability_lines,
        "## Full Tour Itineraries",
        "",
        "\n".join(detail_lines),
        "## Method Notes",
        "- **Exact MILP (HiGHS):** Proves global optimum via DFJ subtour-elimination constraints (`scipy.optimize.milp`).",
        "- **Nearest Neighbour:** Greedy heuristic choosing closest unvisited city ($O(n^2)$).",
        "- **2-Opt & 3-Opt:** Iterative edge-swap local search refining the Nearest Neighbour route. Their runtimes include building that route.",
        "- **Simulated Annealing & Ant Colony:** Stochastic metaheuristics for escaping local optima. "
        "Simulated Annealing iterations scale as max(8000, 50·n²) with a data-calibrated start temperature.",
        "- **Dynamic Programming (Held-Karp):** Computes exact global optimum via Bellman-Held-Karp subproblem memoization ($O(n^2 2^n)$).",
        "- **Brute Force:** Evaluates all $(n - 1)!$ permutations (`algorithm/exact/brute_force/brute_force.py`).",
        "- **Deterministic algorithms** (everything except Simulated Annealing and Ant Colony) return the same tour every run; only their runtime varies.",
        "- **Warm-up:** each algorithm is run once before timing starts and that run is discarded, so one-off start-up costs do not skew the statistics.",
        "",
    ]
    report_file = outputs_dir / f"tsp_loader_{safe_name}_results.md"
    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    return report_file


def write_scalability_report(
    summaries: List[SuiteSummary],
    runs: int = DEFAULT_RUNS,
    seed: int = DEFAULT_SEED,
    outputs_dir: Path = Path("outputs"),
) -> Path:
    """Write a cross-dataset report with runtime-vs-cities and gap-vs-cities line graphs.

    Each algorithm is one line. Algorithms that only ran on one dataset (Brute Force and
    Dynamic Programming, which only run on the smallest dataset) appear as a single marker.
    """
    outputs_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = outputs_dir / CHARTS_DIRNAME
    by_size = {s.n_cities: s for s in sorted(summaries, key=lambda s: s.n_cities)}
    x_values = list(by_size)

    names: List[str] = []
    for summary in by_size.values():
        for res in summary.results:
            if res.series_name not in names:
                names.append(res.series_name)

    time_series: Dict[str, List[Optional[float]]] = {}
    gap_series: Dict[str, List[Optional[float]]] = {}
    for name in names:
        times: List[Optional[float]] = []
        gaps: List[Optional[float]] = []
        for n_cities in x_values:
            summary = by_size[n_cities]
            res = next((r for r in summary.results if r.series_name == name), None)
            opt = find_optimum(summary.results)
            times.append(res.time_stats.mean if res else None)
            gaps.append((res.distance / opt - 1) * 100 if res and opt else None)
        time_series[name] = times
        gap_series[name] = gaps

    runtime_png = save_scaling_line_chart(
        charts_dir / "tsp_loader_scalability_runtime.png",
        f"Mean runtime vs number of cities ({pluralize(runs)} per algorithm)",
        "Mean runtime in seconds (log scale)",
        x_values,
        time_series,
        log_y=True,
    )
    has_gap = any(v is not None for values in gap_series.values() for v in values)
    gap_png = None
    if has_gap:
        gap_png = save_scaling_line_chart(
            charts_dir / "tsp_loader_scalability_gap.png",
            "Best result vs number of cities (gap to proven optimum)",
            "Best-run distance above the proven optimum (%)",
            x_values,
            gap_series,
        )

    headers = ["Algorithm"] + [f"{n} cities" for n in x_values]
    runtime_table = markdown_table(
        headers,
        [[name] + [f"{v:.6f}" if v is not None else "-" for v in time_series[name]] for name in names],
    )
    gap_table = markdown_table(
        headers,
        [[name] + [f"{v:+.2f}%" if v is not None else "-" for v in gap_series[name]] for name in names],
    )

    dataset_lines = [
        f"- **{n} cities:** [{s.suite_name}](tsp_loader_{s.slug or slugify(s.suite_name)}_results.md)"
        for n, s in by_size.items()
    ]
    if has_gap:
        gap_section = [
            f"![Best result vs number of cities]({CHARTS_DIRNAME}/{gap_png.name})",
            "",
            gap_table,
        ]
    else:
        gap_section = ["*Not available: the exact solver was skipped (`--no-exact`), so there is no proven optimum to compare against.*"]

    md_lines = [
        "# TSP Scalability Summary",
        "",
        f"- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Runs per algorithm:** {runs} (plus 1 untimed warm-up run each)",
        f"- **Base seed:** {seed}",
        "- **Datasets:**",
        *[f"  {line}" for line in dataset_lines],
        "",
        "## Runtime vs Number of Cities",
        "",
        f"![Mean runtime vs number of cities]({CHARTS_DIRNAME}/{runtime_png.name})",
        "",
        "Mean runtime in seconds (log scale). 2-Opt and 3-Opt times include building the Nearest Neighbour starting tour.",
        "",
        runtime_table,
        "",
        "## Best Result vs Number of Cities",
        "",
        *gap_section,
        "",
        "> [!NOTE]",
        "> Raw tour distances are not comparable between datasets of different sizes, so the best result is shown as the gap (%) "
        "above the proven optimum. Brute Force and Dynamic Programming only run on the smallest dataset, so they appear as a single marker.",
        "",
    ]
    report_file = outputs_dir / "tsp_loader_scalability_summary.md"
    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    return report_file


def evaluate_suite(
    suite_name: str,
    cities: List[str],
    dist_matrix: List[List[float]],
    run_exact: bool = True,
    run_exact_solvers: bool = True,
    runs: int = DEFAULT_RUNS,
    seed: int = DEFAULT_SEED,
    slug: Optional[str] = None,
) -> SuiteSummary:
    """Execute each TSP algorithm on the given problem instance and report results."""
    print(f"\nEvaluating: {suite_name} ({len(cities)} cities, {pluralize(runs)} each)")
    safe_name = slugify(slug if slug else suite_name)
    sa_params = sa_parameters_for(dist_matrix, seed)
    results = run_benchmarks(
        cities,
        dist_matrix,
        run_exact=run_exact,
        run_exact_solvers=run_exact_solvers,
        runs=runs,
        seed=seed,
        sa_params=sa_params,
    )
    report_file = write_markdown_report(
        suite_name, cities, results, runs=runs, seed=seed, sa_params=sa_params, slug=safe_name,
    )
    csv_file = write_runs_csv(suite_name, results, slug=safe_name)
    print(f"  -> Report written: {report_file}")
    print(f"  -> Charts written: {report_file.parent / CHARTS_DIRNAME}")
    print(f"  -> Raw runs written: {csv_file}")
    return SuiteSummary(suite_name=suite_name, n_cities=len(cities), results=results, slug=safe_name)


def load_cartesian_suite(filepath: str) -> Tuple[List[str], List[List[float]]]:
    """Load city names and distance matrix from an Excel file (Cartesian coordinates or distance matrix)."""
    cities, dist_matrix, _ = load_tsp_data(filepath)
    return cities, dist_matrix


def positive_int(value: str) -> int:
    """argparse type: an integer >= 1."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value!r}")
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1 (got {number})")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified TSP algorithm runner and benchmark suite."
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        help="Optional dataset filepaths to evaluate (e.g. data/coordinates_10_cities.xlsx). "
             "If omitted, runs the default Cartesian suite.",
    )
    parser.add_argument(
        "--no-exact",
        action="store_true",
        help="Skip exact MILP solver baseline.",
    )
    parser.add_argument(
        "--runs",
        "-r",
        type=positive_int,
        default=DEFAULT_RUNS,
        help=f"Number of timed runs per algorithm (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Base random seed for Simulated Annealing and Ant Colony; run i uses seed + i (default: {DEFAULT_SEED})",
    )

    args = parser.parse_args()

    target_files = args.datasets if args.datasets else [fp for fp, _ in CARTESIAN_SUITES]

    summaries: List[SuiteSummary] = []
    for filepath in target_files:
        path = Path(filepath)
        if not path.exists():
            path = PROJECT_ROOT / filepath
        if path.exists():
            cities, dist_matrix, dataset_type = load_tsp_data(str(path))
            n = len(cities)
            # Brute-force & Dynamic Programming (Held-Karp) are exact searches under algorithm/exact evaluated for small instances (n <= 10)
            run_exact_solvers = n <= 10
            summaries.append(evaluate_suite(
                f"{dataset_type} ({n} Cities) - {path.name}",
                cities,
                dist_matrix,
                run_exact=not args.no_exact,
                run_exact_solvers=run_exact_solvers,
                runs=args.runs,
                seed=args.seed,
                slug=path.stem,
            ))
        else:
            print(f"Warning: Dataset file not found: {filepath}", file=sys.stderr)

    if len({s.n_cities for s in summaries}) >= 2:
        scalability_file = write_scalability_report(summaries, runs=args.runs, seed=args.seed)
        print(f"\nScalability summary written: {scalability_file}")
    else:
        print("\nScalability summary skipped: it needs at least two datasets with different city counts.")


if __name__ == "__main__":
    main()

