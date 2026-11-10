"""
Author: Jessie W

Metaheuristic TSP algorithms: Simulated Annealing and Ant Colony Optimization.

Can be imported as a library or executed directly from the command line:
    python metaheuristic.py
    python metaheuristic.py data/cities_20_cartesian.xlsx
    python metaheuristic.py data/distances_20_cities.xlsx --seed 42

Running the script automatically executes both metaheuristics, calculates the exact
global optimum using the project's HiGHS MILP solver with DFJ subtour cuts, plots
their convergence profiles over time, and generates a detailed Markdown report
in the outputs/ directory.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import random
import sys
import time
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Project modules for exact baseline comparison, greedy initialization, charts, and formatting
from nearest_neighbour import (
    build_euclidean_matrix,
    exact_route,
    nearest_neighbour,
    read_cities,
    route_length,
)
from tsp_charts import save_convergence_chart
from tsp_utils import format_gap, markdown_table


class _ConfigMixin:
    """Shared factory helper for converting optional dicts or instances into a dataclass."""

    @classmethod
    def from_config(cls, config: Optional[Union["_ConfigMixin", Dict]]):
        if isinstance(config, cls):
            return config
        if isinstance(config, dict):
            return cls(**{k: v for k, v in config.items() if k in cls.__dataclass_fields__})
        return cls()


@dataclass(frozen=True)
class SAParams(_ConfigMixin):
    """Hyperparameters for Simulated Annealing."""
    t_init: float = 500.0
    alpha: float = 0.997
    max_iter: int = 8000
    seed: Optional[int] = None


@dataclass(frozen=True)
class ACOParams(_ConfigMixin):
    """Hyperparameters for Ant Colony Optimization."""
    n_ants: int = 20
    n_iter: int = 150
    alpha: float = 1.0
    beta: float = 3.0
    evaporation: float = 0.1
    q_deposit: float = 100.0
    e_weight: float = 5.0
    seed: Optional[int] = None


def resolve_sa_schedule(
    t_init: Optional[float],
    alpha: Optional[float],
    max_iter: int,
    use_nn_seed: bool = True,
) -> Tuple[float, float]:
    """Resolve default initial temperature and cooling rate for Simulated Annealing."""
    resolved_t_init = t_init if t_init is not None else (30.0 if use_nn_seed else 500.0)
    if alpha is not None:
        resolved_alpha = alpha
    else:
        t_final = 0.01
        resolved_alpha = (t_final / resolved_t_init) ** (1.0 / max_iter) if max_iter > 0 else 0.997
    return resolved_t_init, resolved_alpha


# 1. DATA LOADERS (Excel Distance Matrix or Cartesian Coordinates)

def load_distance_excel(path: str, sheet_name: int = 0) -> Tuple[List[str], List[List[float]]]:
    """Loads symmetric distance matrix from team's Excel template."""
    df = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
    df.columns = [str(c).strip() for c in df.columns]
    df.index = [str(i).strip() for i in df.index]
    cities = list(df.columns)
    n = len(cities)
    dist_matrix = [[0.0] * n for _ in range(n)]

    for i, a in enumerate(cities):
        for j, b in enumerate(cities):
            val = df.loc[a, b]
            if a != b and not pd.isna(val):
                d = float(val)
                dist_matrix[i][j] = d
                dist_matrix[j][i] = d
    return cities, dist_matrix


def load_tsp_data(path: str, sheet_name: int = 0) -> Tuple[List[str], List[List[float]], str]:
    """
    Auto-detects and loads either Cartesian coordinates (cities_*.xlsx)
    or symmetric distance matrices (distances_*.xlsx).

    Returns (cities, dist_matrix, dataset_type), where dataset_type is
    'Cartesian coordinates' or 'Symmetric distance matrix'.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"TSP data file not found: {file_path}")

    try:
        cities, points = read_cities(str(file_path))
        return cities, build_euclidean_matrix(points), "Cartesian coordinates"
    except ValueError:
        cities, dist_matrix = load_distance_excel(str(file_path), sheet_name=sheet_name)
        return cities, dist_matrix, "Symmetric distance matrix"


# 2. SIMULATED ANNEALING (SA)

def solve_tsp_sa(
    dist_matrix: List[List[float]],
    t_init: Optional[float] = None,
    alpha: Optional[float] = None,
    max_iter: int = 8000,
    seed: int = None,
    use_nn_seed: bool = True,
    initial_route: Optional[List[int]] = None,
) -> Dict:
    """
    Solves TSP using Simulated Annealing with hybrid 2-opt and swap neighbourhoods.

    Tuned Schedule:
      - Initial Temperature (t_init): Defaults to 30.0 when using Nearest Neighbour seeding
        (or 500.0 for random starts). This prevents high-temperature thermal vaporization
        of the high-quality greedy tour structure.
      - Cooling Rate (alpha): When None, automatically computed so that temperature cools
        smoothly from t_init to T_final = 0.01 at max_iter:
            alpha = (0.01 / t_init) ** (1.0 / max_iter)
        This ensures active, productive annealing across the entire iteration budget without
        premature freezing.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    n = len(dist_matrix)
    if initial_route is not None:
        curr_route = list(initial_route)
        if curr_route and curr_route[0] != curr_route[-1]:
            curr_route.append(curr_route[0])
    elif use_nn_seed:
        nn_tour, _ = nearest_neighbour(dist_matrix)
        curr_route = list(nn_tour)
    else:
        curr_route = [0] + random.sample(range(1, n), n - 1) + [0]

    curr_dist = route_length(curr_route, dist_matrix)
    initial_dist = curr_dist
    best_route, best_dist = list(curr_route), curr_dist

    # Apply Tuned Annealing Schedule
    t_init, alpha = resolve_sa_schedule(t_init, alpha, max_iter, use_nn_seed)

    temp = t_init
    history = []
    time_history = []
    conv_iter = 0
    conv_time = 0.0
    t_start = time.perf_counter()

    for it in range(1, max_iter + 1):
        i, j = sorted(random.sample(range(1, n), 2))
        is_2opt = random.random() < 0.7

        if is_2opt:
            delta = calculate_two_opt_delta(curr_route, dist_matrix, i, j)
        else:
            delta = calculate_city_swap_delta(curr_route, dist_matrix, i, j)

        # Metropolis acceptance criterion
        if delta < 0 or random.random() < np.exp(-delta / temp):
            if is_2opt:
                curr_route[i:j + 1] = curr_route[i:j + 1][::-1]
            else:
                curr_route[i], curr_route[j] = curr_route[j], curr_route[i]
            curr_dist += delta
            if curr_dist < best_dist - 1e-9:
                best_route = list(curr_route)
                best_dist = route_length(best_route, dist_matrix)
                curr_dist = best_dist
                conv_iter = it
                conv_time = time.perf_counter() - t_start

        temp *= alpha
        now = time.perf_counter() - t_start
        history.append(best_dist)
        time_history.append(now)

    exec_time = time.perf_counter() - t_start
    return {
        "route": best_route,
        "distance": best_dist,
        "initial_distance": initial_dist,
        "time_sec": exec_time,
        "history": history,
        "time_history": time_history,
        "convergence_iter": conv_iter,
        "conv_time_sec": conv_time,
    }


def calculate_city_swap_delta(
    curr_route: list[int],
    dist_matrix: list[list[float | int]],
    i: int,
    j: int,
) -> float | int:
    prev_i = curr_route[i - 1]
    next_i = curr_route[i + 1]
    prev_j = curr_route[j - 1]
    next_j = curr_route[j + 1]
    if j == i + 1:
        delta = (
            dist_matrix[prev_i][curr_route[j]] + dist_matrix[curr_route[i]][next_j]
            - dist_matrix[prev_i][curr_route[i]] - dist_matrix[curr_route[j]][next_j]
        )
    else:
        delta = (
            dist_matrix[prev_i][curr_route[j]] + dist_matrix[curr_route[j]][next_i]
            + dist_matrix[prev_j][curr_route[i]] + dist_matrix[curr_route[i]][next_j]
            - dist_matrix[prev_i][curr_route[i]] - dist_matrix[curr_route[i]][next_i]
            - dist_matrix[prev_j][curr_route[j]] - dist_matrix[curr_route[j]][next_j]
        )
    return delta


def calculate_two_opt_delta(
    curr_route: list[int],
    dist_matrix: list[list[float | int]],
    i: int,
    j: int,
) -> float | int:
    u_prev_i = curr_route[i - 1]
    u_i = curr_route[i]
    u_j = curr_route[j]
    u_next_j = curr_route[j + 1]
    return (
        dist_matrix[u_prev_i][u_j] + dist_matrix[u_i][u_next_j]
        - dist_matrix[u_prev_i][u_i] - dist_matrix[u_j][u_next_j]
    )


# 3. ANT COLONY OPTIMISATION (ACO)

def _deposit_pheromone(pheromone: np.ndarray, route: List[int], amount: float) -> None:
    """Add symmetric pheromone deposit along every consecutive edge in a closed route."""
    for u, v in zip(route, route[1:]):
        pheromone[u][v] += amount
        pheromone[v][u] += amount


def solve_tsp_aco(
    dist_matrix: List[List[float]],
    n_ants: int = 20,
    n_iter: int = 150,
    alpha: float = 1.0,
    beta: float = 3.0,
    evaporation: float = 0.1,
    q_deposit: float = 100.0,
    e_weight: float = 5.0,
    seed: int = None
) -> Dict:
    """
    Solves TSP using Ant Colony Optimisation with Elitist Ant System (EAS) reinforcement.
    In addition to all ants depositing pheromone, the best-so-far tour gets a bonus weight,
    accelerating convergence to superior solutions.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    n = len(dist_matrix)
    pheromone = np.full((n, n), 0.1)
    heuristic = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j and dist_matrix[i][j] > 0:
                heuristic[i][j] = 1.0 / dist_matrix[i][j]

    # Precompute static heuristic desirability raised to beta power (O(1) lookup during search)
    heuristic_pow = (heuristic ** beta).tolist()

    best_route, best_dist = [], float("inf")
    initial_dist = None
    history = []
    time_history = []
    conv_iter = 0
    conv_time = 0.0
    t_start = time.perf_counter()

    for it in range(1, n_iter + 1):
        all_routes, all_dists = [], []
        pheromone_pow = pheromone if alpha == 1.0 else pheromone ** alpha
        for _ in range(n_ants):
            curr = 0
            visited = {0}
            route = [0]
            while len(visited) < n:
                unvisited = [j for j in range(n) if j not in visited]
                weights = [
                    pheromone_pow[curr][j] * heuristic_pow[curr][j]
                    for j in unvisited
                ]
                nxt = random.choices(unvisited, weights=weights, k=1)[0]
                route.append(nxt)
                visited.add(nxt)
                curr = nxt
            route.append(0)

            d = route_length(route, dist_matrix)
            all_routes.append(route)
            all_dists.append(d)
            if d < best_dist:
                best_route, best_dist = list(route), d
                conv_iter = it
                conv_time = time.perf_counter() - t_start

        if initial_dist is None and all_dists:
            initial_dist = min(all_dists)

        # Pheromone update: evaporation + new deposits
        pheromone *= (1.0 - evaporation)
        for route, d in zip(all_routes, all_dists):
            _deposit_pheromone(pheromone, route, q_deposit / d)

        # Elitist reinforcement on best-so-far tour (Optimisation B)
        if best_route and e_weight > 0:
            _deposit_pheromone(pheromone, best_route, (e_weight * q_deposit) / best_dist)

        now = time.perf_counter() - t_start
        history.append(best_dist)
        time_history.append(now)

    exec_time = time.perf_counter() - t_start
    return {
        "route": best_route,
        "distance": best_dist,
        "initial_distance": initial_dist if initial_dist is not None else best_dist,
        "time_sec": exec_time,
        "history": history,
        "time_history": time_history,
        "convergence_iter": conv_iter,
        "conv_time_sec": conv_time,
    }


# 4. CONVERGENCE REPORTING

def _extract_milestones(res: Dict, total_iters: int, optimum: Optional[float]) -> List[Tuple[str, int, float, float, str]]:
    """
    Extracts progress rows for milestone tables:
    (Milestone label, Iteration, Elapsed time, Best distance, Gap to optimum string).
    """
    rows = []
    hist = res["history"]
    time_hist = res["time_history"]
    n_pts = len(hist)

    def gap_str(d: float) -> str:
        return format_gap(d, optimum, precision=4, zero_label="0.0000% (Optimal)")

    # Initial state
    init_dist = res.get("initial_distance", hist[0])
    rows.append(("Initial Route", 0, 0.0, init_dist, gap_str(init_dist)))

    # Percent checkpoints
    checkpoints = [10, 25, 50, 75, 100]
    for p in checkpoints:
        idx = min(n_pts - 1, max(0, int(round((p / 100.0) * n_pts)) - 1))
        label = f"{p}% Budget"
        it_num = idx + 1
        t_sec = time_hist[idx]
        d = hist[idx]
        rows.append((label, it_num, t_sec, d, gap_str(d)))

    # Convergence point (Best found)
    conv_it = res["convergence_iter"]
    conv_t = res["conv_time_sec"]
    conv_d = res["distance"]
    pct = (conv_it / total_iters) * 100.0 if total_iters > 0 else 0.0
    best_label = f"**Best Discovered ({pct:.1f}%)**"
    rows.append((best_label, conv_it, conv_t, conv_d, gap_str(conv_d)))

    # Sort so best discovered is in order or clearly marked
    # We will display standard checkpoints then highlight the convergence point
    return rows


def save_metaheuristic_report(
    input_file: str,
    dataset_type: str,
    cities: List[str],
    sa_res: Dict,
    aco_res: Dict,
    optimum_route: Optional[List[int]],
    optimum_dist: Optional[float],
    exact_time_sec: Optional[float],
    output_dir: str = "outputs",
    chart_rel_path: str = "charts",
    sa_params: Optional[Union[SAParams, Dict]] = None,
    aco_params: Optional[Union[ACOParams, Dict]] = None,
) -> Path:
    """
    Constructs and writes the complete convergence Markdown report.
    """
    outputs_path = Path(output_dir)
    outputs_path.mkdir(parents=True, exist_ok=True)
    stem = Path(input_file).stem
    report_file = outputs_path / f"{stem}_metaheuristic_results.md"
    chart_file = f"{stem}_convergence.png"

    sa_cfg = SAParams.from_config(sa_params)
    aco_cfg = ACOParams.from_config(aco_params)

    sa_dist = sa_res["distance"]
    aco_dist = aco_res["distance"]
    algo_runs = [
        ("Simulated Annealing", sa_res),
        ("Ant Colony Optimization", aco_res),
    ]

    def gap_str(val: float) -> str:
        return format_gap(val, optimum_dist, precision=4, zero_label="0.0000%")

    def calc_quality(val: float) -> str:
        if optimum_dist is None or optimum_dist <= 0:
            return "N/A"
        return f"{100.0 * val / optimum_dist:.4f}%"

    sa_opt_hit = "Yes" if (optimum_dist and abs(sa_dist - optimum_dist) < 1e-4) else "No"
    aco_opt_hit = "Yes" if (optimum_dist and abs(aco_dist - optimum_dist) < 1e-4) else "No"

    lines = [
        "# Metaheuristic TSP Algorithms: Convergence Report",
        "",
        f"**Input Dataset:** `{Path(input_file).name}` ({dataset_type})  ",
        f"**Cities Evaluated:** {len(cities)} (Origin/Depot: `{cities[0]}`)  ",
    ]

    if optimum_dist is not None:
        lines += [
            f"**Proven Global Optimum:** `{optimum_dist:.6f}` "
            f"(proven via HiGHS MILP solver with DFJ subtour cuts in {exact_time_sec:.4f} s)  ",
        ]
    else:
        lines += [
            "**Proven Global Optimum:** Not computed (`--no-exact` enabled)  ",
        ]

    comparison_table = markdown_table(
        ["Performance Metric", "Simulated Annealing", "Ant Colony Optimization"],
        [
            ["Initial Tour Distance", f"{sa_res.get('initial_distance', 0.0):.6f}", f"{aco_res.get('initial_distance', 0.0):.6f}"],
            ["Final Best Tour Distance", f"**{sa_dist:.6f}**", f"**{aco_dist:.6f}**"],
            ["Distance Above Optimum (%)", f"**{gap_str(sa_dist)}**", f"**{gap_str(aco_dist)}**"],
            ["Solution Quality (% of Optimum)", calc_quality(sa_dist), calc_quality(aco_dist)],
            ["Proven Optimum Reached?", f"**{sa_opt_hit}**", f"**{aco_opt_hit}**"],
            ["Convergence Iteration", f"{sa_res['convergence_iter']:,} / {len(sa_res['history']):,}", f"{aco_res['convergence_iter']:,} / {len(aco_res['history']):,}"],
            ["Budget Consumed at Best Tour", f"{(sa_res['convergence_iter'] / len(sa_res['history'])) * 100:.2f}%", f"{(aco_res['convergence_iter'] / len(aco_res['history'])) * 100:.2f}%"],
            ["Time to Discover Best Tour", f"{sa_res['conv_time_sec']:.6f} s", f"{aco_res['conv_time_sec']:.6f} s"],
            ["Total Wall-Clock Execution Time", f"{sa_res['time_sec']:.6f} s", f"{aco_res['time_sec']:.6f} s"],
        ],
        alignments=[":---", "---:", "---:"],
    )

    lines += [
        "",
        "---",
        "",
        "## Convergence Visualizations",
        "",
        f"![Convergence of Metaheuristics over Time]({chart_rel_path}/{chart_file})",
        "",
        "*Figure: Left panel displays best-so-far tour distance as a function of elapsed wall-clock seconds. "
        "Right panel displays convergence relative to total iteration budget progress (%). "
        "The dashed green line marks the exact global optimum proven by HiGHS MILP.*",
        "",
        "---",
        "",
        "## Executive Performance & Convergence Comparison",
        "",
        comparison_table,
        "",
        "---",
        "",
        "## Convergence Milestones Across Time",
    ]

    milestone_headers = ["Milestone Checkpoint", "Iteration", "Elapsed Time", "Best Tour Distance", "Gap vs. Optimum"]
    milestone_align = [":---", "---:", "---:", "---:", "---:"]
    for algo_name, res in algo_runs:
        milestones = _extract_milestones(res, len(res["history"]), optimum_dist)
        milestone_table = markdown_table(
            milestone_headers,
            [[label, f"{it_num:,}", f"{t_sec:.6f} s", f"{d:.6f}", gap] for label, it_num, t_sec, d, gap in milestones],
            alignments=milestone_align,
        )
        lines += [
            "",
            f"### {algo_name} Convergence Progression",
            "",
            milestone_table,
        ]

    lines += [
        "",
        "---",
        "",
        "## Algorithm Configurations",
        "",
        "### Simulated Annealing Hyperparameters",
        f"- **Initial Temperature ($T_0$):** {sa_cfg.t_init}",
        f"- **Cooling Schedule Rate ($\\alpha$):** {sa_cfg.alpha} (geometric cooling $T_{{k+1}} = \\alpha \\cdot T_k$)",
        f"- **Maximum Iterations:** {sa_cfg.max_iter:,} iterations",
        "- **Neighborhood Operators:** 70% 2-Opt segment reversals (untangling crossed paths), 30% 2-City coordinate swaps",
        f"- **Random Seed:** {sa_cfg.seed}",
        "",
        "### Ant Colony Optimization Hyperparameters",
        f"- **Colony Size ($m$):** {aco_cfg.n_ants} artificial ants per iteration",
        f"- **Colony Iterations ($I$):** {aco_cfg.n_iter} iterations ({aco_cfg.n_ants * aco_cfg.n_iter:,} total evaluated tours)",
        f"- **Pheromone Influence ($\\alpha$):** {aco_cfg.alpha}",
        f"- **Heuristic Visibility Influence ($\\beta$):** {aco_cfg.beta} (visibility $\\eta_{{ij}} = 1 / d_{{ij}}$)",
        f"- **Pheromone Evaporation Rate ($\\rho$):** {aco_cfg.evaporation}",
        f"- **Deposit Constant ($Q$):** {aco_cfg.q_deposit}",
        f"- **Random Seed:** {aco_cfg.seed}",
        "",
        "---",
        "",
        "## Final Tour Itineraries",
        "",
    ]

    # Format tours
    def format_tour_list(tour_indices: List[int]) -> List[str]:
        return [f"{idx}. {cities[c]}" for idx, c in enumerate(tour_indices, 1)]

    if optimum_route:
        lines += [
            "### Proven Optimal Tour (HiGHS MILP)",
            "",
            f"**Distance:** `{optimum_dist:.6f}`",
            "",
            *format_tour_list(optimum_route),
            "",
        ]

    for algo_name, res in algo_runs:
        dist = res["distance"]
        lines += [
            f"### {algo_name} Best Tour",
            "",
            f"**Distance:** `{dist:.6f}` ({gap_str(dist)} vs. optimum)",
            "",
            *format_tour_list(res["route"]),
            "",
        ]

    lines += [
        "---",
        "",
        "## Methodological Notes",
        "",
        "1. **Exploration vs. Exploitation Dynamics:**",
        "   - **Simulated Annealing** starts with high thermal energy ($T_0$), allowing large uphill moves with high probability to cross energy barriers and avoid early entrapment in shallow local minima. As temperature geometric cools ($T \\to 0$), acceptance of degrading moves drops to zero, smoothly transitioning the search into greedy local refinement via 2-opt and swap moves.",
        "   - **Ant Colony Optimization** operates via collective swarm intelligence. Initially, uniform pheromone distribution encourages broad stochastic exploration influenced primarily by greedy distance visibility ($1 / d_{ij}$). As iterations progress, shorter tours deposit proportionally higher pheromone quantities ($Q / L$), while evaporation ($1 - \\rho$) decays abandoned trails, focusing subsequent ant generations onto high-quality sub-paths.",
        "2. **Computational Budget Comparison:**",
        f"   - Simulated Annealing performs {len(sa_res['history']):,} single-move candidate evaluations, requiring minimal memory and execution overhead.",
        f"   - Ant Colony Optimization constructs full tours for all {aco_cfg.n_ants} ants every iteration ({len(aco_res['history']) * aco_cfg.n_ants:,} complete TSP routes). Although evaluating fewer outer iterations, each generation performs extensive matrix probability sampling.",
        "3. **Exact Solver Baseline:**",
        "   - The reference optimal distance is solved using HiGHS Mixed-Integer Linear Programming (`scipy.optimize.milp`) with dynamic Dantzig-Fulkerson-Johnson (DFJ) subtour-elimination cuts, guaranteeing a proven global optimum (MIP gap = 0.0) without distance discretization.",
        "",
    ]

    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_file


# 5. COMMAND-LINE INTERFACE & ENTRYPOINT

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run Simulated Annealing and Ant Colony Optimization and generate a convergence Markdown report with embedded plots."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        default="data/cities_20_cartesian.xlsx",
        help="Path to TSP dataset (.xlsx Cartesian coordinates or symmetric distance matrix). Default: data/cities_20_cartesian.xlsx",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility. Default: 42",
    )
    parser.add_argument(
        "--sa-iter",
        type=int,
        default=8000,
        help="Maximum iterations for Simulated Annealing. Default: 8000",
    )
    parser.add_argument(
        "--sa-temp",
        type=float,
        default=None,
        help="Initial temperature for Simulated Annealing. Default: auto-tuned 30.0 for NN start (500.0 for random).",
    )
    parser.add_argument(
        "--sa-alpha",
        type=float,
        default=None,
        help="Cooling rate for Simulated Annealing. Default: auto-tuned so cooling spans the full iteration budget.",
    )
    parser.add_argument(
        "--aco-iter",
        type=int,
        default=150,
        help="Number of iterations for Ant Colony Optimization. Default: 150",
    )
    parser.add_argument(
        "--aco-ants",
        type=int,
        default=20,
        help="Number of ants for Ant Colony Optimization. Default: 20",
    )
    parser.add_argument(
        "--aco-e-weight",
        type=float,
        default=5.0,
        help="Elitist pheromone reinforcement weight for ACO best-so-far tour. Default: 5.0 (0 disables).",
    )
    parser.add_argument(
        "--sa-random-start",
        action="store_true",
        help="Use a purely random starting route for Simulated Annealing instead of greedy Nearest Neighbour seeding.",
    )
    parser.add_argument(
        "--no-exact",
        action="store_true",
        help="Skip computing the exact HiGHS MILP optimum baseline.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save generated Markdown report and charts. Default: outputs",
    )

    args = parser.parse_args(argv)

    actual_t_init, actual_alpha = resolve_sa_schedule(
        args.sa_temp, args.sa_alpha, args.sa_iter, use_nn_seed=not args.sa_random_start,
    )

    print("=" * 72)
    print("METAHEURISTIC TSP ALGORITHMS - CONVERGENCE RUNNER")
    print("=" * 72)
    print(f"Dataset path:      {args.dataset}")
    print(f"Random seed:       {args.seed}")
    print(f"SA iterations:     {args.sa_iter:,} (T0={actual_t_init:.1f}, alpha={actual_alpha:.6f}, start={'random' if args.sa_random_start else 'nearest_neighbour'})")
    print(f"ACO iterations:    {args.aco_iter:,} (ants={args.aco_ants}, elitist_weight={args.aco_e_weight})")
    print("-" * 72)

    # 1. Load Data
    try:
        cities, dist_matrix, dataset_type = load_tsp_data(args.dataset)
    except Exception as exc:
        print(f"Error loading dataset '{args.dataset}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(cities)} cities [{dataset_type}]. Start/depot: '{cities[0]}'")

    # 2. Compute Exact Optimum Baseline (unless skipped)
    optimum_dist = None
    optimum_route = None
    exact_time_sec = 0.0

    if not args.no_exact:
        print("Computing proven global optimum via HiGHS MILP solver...")
        t0 = time.perf_counter()
        try:
            optimum_route = exact_route(dist_matrix)
            exact_time_sec = time.perf_counter() - t0
            optimum_dist = route_length(optimum_route, dist_matrix)
            print(f"Exact optimum:     {optimum_dist:.6f} (found in {exact_time_sec:.4f} s)")
        except Exception as exc:
            print(f"Warning: Exact solver could not prove optimum ({exc}). Proceeding without exact baseline.")
            optimum_dist = None
            optimum_route = None
    else:
        print("Skipping exact MILP baseline search.")

    def print_run_summary(label: str, res: Dict, total_iters: int) -> None:
        gap = format_gap(res["distance"], optimum_dist, precision=4)
        print(
            f"{label:<19}best={res['distance']:.4f} (gap: {gap}), "
            f"converged at iter {res['convergence_iter']:,}/{total_iters:,} ({res['conv_time_sec']:.4f} s), "
            f"total time: {res['time_sec']:.4f} s"
        )

    # 3. Run Simulated Annealing
    print("Running Simulated Annealing...")
    sa_res = solve_tsp_sa(
        dist_matrix,
        t_init=actual_t_init,
        alpha=actual_alpha,
        max_iter=args.sa_iter,
        seed=args.seed,
        use_nn_seed=not args.sa_random_start,
    )
    print_run_summary("SA finished:", sa_res, args.sa_iter)

    # 4. Run Ant Colony Optimization
    print("Running Ant Colony Optimization...")
    aco_res = solve_tsp_aco(
        dist_matrix,
        n_ants=args.aco_ants,
        n_iter=args.aco_iter,
        e_weight=args.aco_e_weight,
        seed=args.seed,
    )
    print_run_summary("ACO finished:", aco_res, args.aco_iter)

    # 5. Generate Matplotlib Convergence Chart
    outputs_path = Path(args.output_dir)
    charts_path = outputs_path / "charts"
    stem = Path(args.dataset).stem
    chart_file = charts_path / f"{stem}_convergence.png"

    print("Generating convergence plots...")
    chart_title = f"TSP Convergence Over Time - {Path(args.dataset).name} ({len(cities)} Cities)"
    save_convergence_chart(
        chart_file,
        chart_title,
        sa_res,
        aco_res,
        optimum=optimum_dist,
    )
    print(f"Chart saved:       {chart_file.resolve()}")

    # 6. Save Markdown Report
    print("Writing Markdown report...")
    sa_params = SAParams(
        t_init=round(actual_t_init, 2),
        alpha=round(actual_alpha, 6),
        max_iter=args.sa_iter,
        seed=args.seed,
    )
    aco_params = ACOParams(
        n_ants=args.aco_ants,
        n_iter=args.aco_iter,
        e_weight=args.aco_e_weight,
        seed=args.seed,
    )

    report_path = save_metaheuristic_report(
        input_file=args.dataset,
        dataset_type=dataset_type,
        cities=cities,
        sa_res=sa_res,
        aco_res=aco_res,
        optimum_route=optimum_route,
        optimum_dist=optimum_dist,
        exact_time_sec=exact_time_sec,
        output_dir=args.output_dir,
        chart_rel_path="charts",
        sa_params=sa_params,
        aco_params=aco_params,
    )
    print(f"Report saved:      {report_path.resolve()}")
    print("=" * 72)
    print(f"SUCCESS: Convergence Markdown report generated at:\n  {report_path.resolve()}")
    print("=" * 72)


if __name__ == "__main__":
    main()