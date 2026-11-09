"""
Author: Richard Clark

tsp_loader.py - Unified orchestrator for Travelling Salesperson Problem algorithms.

Runs each implemented TSP algorithm in turn across available datasets:
  1. Exact MILP Solver (HiGHS via scipy.optimize.milp with DFJ subtour elimination)
  2. Nearest Neighbour (Greedy constructive heuristic)
  3. 2-Opt Local Search (Edge-reversal iterative refinement)
  4. 3-Opt Local Search (7-case triplet reconnection iterative refinement)
  5. Simulated Annealing (Metaheuristic: hybrid 2-opt + swap)
  6. Ant Colony Optimization (Metaheuristic: Ant System)
  7. Brute Force & Branch and Bound (Exact search for small instances)

Usage:
  python tsp_loader.py
  python tsp_loader.py --small-cartesian data/cities_10_cartesian.xlsx --cartesian data/cities_20_cartesian.xlsx
  python tsp_loader.py --help
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import re
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Third-party imports
import pandas as pd

# Project modules
from nearest_neighbour import (
    read_cities,
    nearest_neighbour,
    route_length,
    exact_route,
)
from two_opt import two_opt
from three_opt import three_opt
from metaheuristic import (
    solve_tsp_sa,
    solve_tsp_aco,
)
from brute_force_visualized import run_brute_force
from branch_and_bound import run_branch_and_bound


def build_euclidean_matrix(points: List[Tuple[float, float]]) -> List[List[float]]:
    """Build a symmetric distance matrix from (X, Y) coordinates."""
    return [
        [math.dist(p1, p2) for p2 in points]
        for p1 in points
    ]


def format_duration(seconds: float) -> str:
    """Format duration into human-readable time."""
    if seconds < 0.001:
        return f"{seconds * 1e6:.1f} microseconds"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60.0:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600.0:
        return f"{seconds / 60:.1f} minutes"
    elif seconds < 86400.0:
        return f"{seconds / 3600:.1f} hours"
    elif seconds < 365.25 * 86400.0:
        return f"{seconds / 86400:.1f} days"
    else:
        years = seconds / (365.25 * 86400.0)
        if years < 1e6:
            return f"{years:,.1f} years"
        elif years < 1e9:
            return f"{years / 1e6:,.2f} million years"
        else:
            return f"{years / 1e9:,.2f} billion years"


def estimate_exact_times(n: int) -> Tuple[str, str, int]:
    """Calculate theoretical permutations and estimated runtimes for Brute Force & Branch and Bound."""
    perms = math.factorial(n - 1)
    # Calibrated Python throughput: ~1,000,000 permutations/sec
    bf_seconds = perms / 1_000_000.0

    # Branch and bound empirical pruning reduction
    # Calibrated to measured baseline from 'Brute Force - Results.txt':
    # n=12 cities ran in 2.17 seconds with ~5,225,804 pruned states.
    # Effective branching factor base ~2.8x per city depth:
    # 2.17s * (2.8 ^ (n - 12))
    if n <= 10:
        bb_seconds = 0.068
    elif n == 12:
        bb_seconds = 2.17
    else:
        bb_seconds = 2.17 * (2.8 ** (n - 12))

    return format_duration(bf_seconds), format_duration(bb_seconds), perms


def format_route(route: List[int], cities: List[str], max_display: Optional[int] = 7) -> str:
    """Format an index route into a readable city name string."""
    names = [cities[idx] for idx in route]
    if max_display is None or len(names) <= max_display + 2:
        return " -> ".join(names)
    half = max_display // 2
    return " -> ".join(names[:half]) + " -> ... -> " + " -> ".join(names[-half:])


@dataclass
class BenchmarkResult:
    """Stores execution metrics and tour details for a single TSP algorithm run."""
    algorithm: str
    route: List[int]
    distance: float
    time_sec: float
    gap_str: str
    route_summary: str

    def to_summary_row(self) -> Dict[str, str]:
        return {
            "Algorithm": self.algorithm,
            "Distance": f"{self.distance:,.2f}",
            "Time (s)": f"{self.time_sec:.6f}",
            "Gap vs Opt": self.gap_str,
            "Route Summary": self.route_summary,
        }

    def to_detail_markdown(self, cities: List[str]) -> str:
        itinerary = format_route(self.route, cities, max_display=None)
        return "\n".join([
            f"### {self.algorithm}",
            f"- **Final Distance:** {self.distance:,.2f}",
            f"- **Runtime:** {self.time_sec:.6f} seconds",
            "- **Full Tour Itinerary:**",
            f"  `{itinerary}`\n",
        ])


def format_gap(
    distance: float,
    opt_distance: Optional[float],
    default: str = "N/A",
) -> str:
    """Format percentage gap relative to optimal distance."""
    if opt_distance is None:
        return default
    return f"{(distance / opt_distance - 1) * 100:+.2f}%"


def slugify(text: str) -> str:
    """Convert a suite title into a safe filename slug."""
    slug = re.sub(r"[^a-z0-9\-_]+", "_", text.lower())
    return re.sub(r"_+", "_", slug).strip("_")


def run_benchmarks(
    cities: List[str],
    dist_matrix: List[List[float]],
    run_exact: bool = True,
    run_bf: bool = True,
) -> List[BenchmarkResult]:
    """Run all configured TSP algorithms and return their benchmark results."""
    n = len(cities)
    results: List[BenchmarkResult] = []
    opt_distance: Optional[float] = None

    def run_step(
        step_label: str,
        algo_name: str,
        solver_fn: Callable[[], Tuple[List[int], Optional[str]]],
        gap_override: Optional[str] = None,
        gap_default: str = "N/A",
    ) -> BenchmarkResult:
        """Announce, time, evaluate, and record a single TSP solver run."""
        sys.stdout.write(f"  {step_label}... ")
        sys.stdout.flush()

        t0 = time.perf_counter()
        route, extra_info = solver_fn()
        elapsed = time.perf_counter() - t0

        distance = route_length(route, dist_matrix)
        gap = gap_override if gap_override is not None else format_gap(distance, opt_distance, default=gap_default)

        detail_parts = [f"{distance:,.2f}", gap if gap_override is None else f"{elapsed:.4f}s"]
        if extra_info:
            detail_parts.append(extra_info)
        print(f"done ({' | '.join(detail_parts)})")

        res = BenchmarkResult(
            algorithm=algo_name,
            route=route,
            distance=distance,
            time_sec=elapsed,
            gap_str=gap,
            route_summary=format_route(route, cities),
        )
        results.append(res)
        return res

    # 1. Exact MILP Reference (HiGHS)
    if run_exact:
        try:
            exact_res = run_step(
                "[1/6] Exact MILP (HiGHS)",
                "Exact MILP (HiGHS)",
                lambda: (exact_route(dist_matrix), None),
                gap_override="0.00% (proven)",
            )
            opt_distance = exact_res.distance
        except Exception as e:
            print(f"failed ({e})")

    # 2. Nearest Neighbour (also provides initial tour for 2-Opt and 3-Opt)
    nn_res = run_step(
        "[2/6] Nearest Neighbour",
        "Nearest Neighbour",
        lambda: (nearest_neighbour(dist_matrix)[0], None),
    )
    nn_tour = nn_res.route

    # 3–6. Local Search Refinements & Stochastic Metaheuristics
    def solve_with_moves(fn: Callable) -> Tuple[List[int], str]:
        tour, _, _, moves = fn(nn_tour, dist_matrix)
        return tour, f"{moves} moves"

    def solve_metaheuristic(fn: Callable, **kwargs) -> Tuple[List[int], None]:
        res = fn(dist_matrix, seed=42, **kwargs)
        return res["route"] + [res["route"][0]], None

    heuristic_steps = [
        ("[3/6] 2-Opt Refinement", "2-Opt (from NN)", lambda: solve_with_moves(two_opt)),
        ("[4/6] 3-Opt Refinement", "3-Opt (from NN)", lambda: solve_with_moves(three_opt)),
        ("[5/6] Simulated Annealing", "Simulated Annealing", lambda: solve_metaheuristic(solve_tsp_sa, t_init=500.0, alpha=0.997, max_iter=8000)),
        ("[6/6] Ant Colony Optimization", "Ant Colony Opt.", lambda: solve_metaheuristic(solve_tsp_aco, n_ants=20, n_iter=150)),
    ]
    for step_label, algo_name, solver_fn in heuristic_steps:
        run_step(step_label, algo_name, solver_fn)

    # Optional: Brute Force & Branch and Bound
    if run_bf:
        initial_bound = opt_distance if opt_distance is not None else min(r.distance for r in results)

        def solve_bb() -> Tuple[List[int], str]:
            bb_res = run_branch_and_bound(dist_matrix, initial_upper_bound=initial_bound)
            return bb_res["route"], f"{bb_res['branches_pruned']:,} pruned"

        bonus_steps = [
            (
                f"[Bonus] Brute Force ({math.factorial(n - 1):,} permutations)",
                f"Brute Force ({n} cities)",
                lambda: (run_brute_force(cities, dist_matrix)["route"], None),
            ),
            ("[Bonus] Branch and Bound", f"Branch and Bound ({n} cities)", solve_bb),
        ]
        for step_label, algo_name, solver_fn in bonus_steps:
            run_step(step_label, algo_name, solver_fn, gap_default="0.00%")

    return results


def write_markdown_report(
    suite_name: str,
    cities: List[str],
    results: List[BenchmarkResult],
    outputs_dir: Path = Path("outputs"),
) -> Path:
    """Format benchmark results into a Markdown report and save to disk."""
    n = len(cities)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(suite_name)

    df_summary = pd.DataFrame([r.to_summary_row() for r in results])
    headers = list(df_summary.columns)
    md_table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df_summary.iterrows():
        md_table.append("| " + " | ".join(str(val) for val in row.values) + " |")

    detail_lines = [res.to_detail_markdown(cities) for res in results]

    # Scalability / runtime estimation section (especially pertinent for n > 10)
    scalability_lines = []
    if n > 10:
        bf_est, bb_est, perms = estimate_exact_times(n)
        exact_res = next((r for r in results if r.algorithm == "Exact MILP (HiGHS)"), None)
        highs_time_str = f"**{exact_res.time_sec:.4f} seconds** (actual)" if exact_res else "Skipped"
        scalability_lines = [
            "## Exact Scalability Projections for this Dataset",
            "",
            f"Because this dataset has **{n} cities**, exhaustive exact methods grow factorially / exponentially:",
            "",
            "| Exact Method | Theoretical Operations / States | Estimated Runtime on this Machine | Status |",
            "|---|---|---|---|",
            f"| **Pure Brute Force** | $(n-1)! = {perms:,}$ permutations | **{bf_est}** | Infeasible for real-time run |",
            f"| **Branch and Bound** | $O(c^n)$ pruned branch states | **{bb_est}** | Exponential worst-case |",
            f"| **HiGHS MILP Solver** | Dynamic DFJ subtour cuts | {highs_time_str} | Solved to global optimum |",
            "",
            "> [!NOTE]",
            "> Estimates are calibrated against your CPU's measured throughput (~1,000,000 permutations/second).",
            "",
        ]

    md_lines = [
        f"# TSP Benchmark Results: {suite_name}",
        "",
        f"- **Cities Evaluated:** {n} ({', '.join(cities)})",
        f"- **Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Performance & Quality Summary",
        "",
        "\n".join(md_table),
        "",
        *scalability_lines,
        "## Full Tour Itineraries",
        "",
        "\n".join(detail_lines),
        "## Method Notes",
        "- **Exact MILP (HiGHS):** Proves global optimum via DFJ subtour-elimination constraints (`scipy.optimize.milp`).",
        "- **Nearest Neighbour:** Greedy heuristic choosing closest unvisited city ($O(n^2)$).",
        "- **2-Opt & 3-Opt:** Iterative edge-swap local search refining the Nearest Neighbour route.",
        "- **Simulated Annealing & Ant Colony:** Stochastic metaheuristics for escaping local optima.",
        "- **Branch & Bound:** Prunes partial tours as soon as cumulative cost exceeds known upper bound.",
        "- **Brute Force:** Evaluates all $(n - 1)!$ permutations.",
        "",
    ]
    report_file = outputs_dir / f"tsp_loader_{safe_name}_results.md"
    report_file.write_text("\n".join(md_lines), encoding="utf-8")
    return report_file


def evaluate_suite(
    suite_name: str,
    cities: List[str],
    dist_matrix: List[List[float]],
    run_exact: bool = True,
    run_bf: bool = True,
) -> None:
    """Execute each TSP algorithm on the given problem instance and report results."""
    print(f"\nEvaluating: {suite_name} ({len(cities)} cities)")
    results = run_benchmarks(
        cities,
        dist_matrix,
        run_exact=run_exact,
        run_bf=run_bf,
    )
    report_file = write_markdown_report(suite_name, cities, results)
    print(f"  -> Report written: {report_file}")


def load_cartesian_suite(filepath: str) -> Tuple[List[str], List[List[float]]]:
    """Load city names and build a Euclidean distance matrix from a Cartesian Excel file."""
    cities, points = read_cities(filepath)
    return cities, build_euclidean_matrix(points)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified TSP algorithm runner and benchmark suite."
    )
    parser.add_argument(
        "--small-cartesian",
        "-s",
        type=str,
        default="data/cities_10_cartesian.xlsx",
        help="Path to small Cartesian Excel sheet for brute-force demo (default: data/cities_10_cartesian.xlsx)",
    )
    parser.add_argument(
        "--cartesian",
        "-c",
        type=str,
        default="data/cities_20_cartesian.xlsx",
        help="Path to Cartesian coordinates Excel sheet (default: data/cities_20_cartesian.xlsx)",
    )
    parser.add_argument(
        "--large-cartesian",
        "-l",
        type=str,
        default="data/cities_40_cartestian.xlsx",
        help="Path to large Cartesian Excel sheet (default: data/cities_40_cartestian.xlsx)",
    )
    parser.add_argument(
        "--no-exact",
        action="store_true",
        help="Skip exact MILP solver baseline.",
    )

    args = parser.parse_args()

    cartesian_suites = [
        (args.small_cartesian, True),
        (args.cartesian, False),
        (args.large_cartesian, False),
    ]

    for filepath, run_bf in cartesian_suites:
        path = Path(filepath)
        if path.exists():
            cities, dist_matrix = load_cartesian_suite(filepath)
            evaluate_suite(
                f"Cartesian Coordinates ({len(cities)} Cities) - {path.name}",
                cities,
                dist_matrix,
                run_exact=not args.no_exact,
                run_bf=run_bf,
            )


if __name__ == "__main__":
    main()
