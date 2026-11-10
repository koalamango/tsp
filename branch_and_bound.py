"""
Author: Oshanda Hembathanthrige

Keep this file in the SAME FOLDER as nearest_neighbour.py.

Run: py branch_and_bound.py "C:/path/cities.xlsx"

Solves the TSP using exact Branch and Bound with partial-tour pruning.
It imports shared functions from nearest_neighbour.py.
"""
from __future__ import annotations

import math
import sys
import time
from typing import Dict, List, Optional

from nearest_neighbour import (
    build_euclidean_matrix,
    read_cities,
    nearest_neighbour,
    route_length,
    save_report,
)


def branch_and_bound(
    distances: List[List[float]],
    initial_upper_bound: Optional[float] = None,
):
    """Exact branch-and-bound solver with partial-tour pruning.

    Returns (best_route, best_dist, complete_routes, branches_pruned).
    """
    n = len(distances)

    # Precompute minimum outgoing edge per city for admissibility bound
    min_outgoing = [
        min(distances[i][j] for j in range(n) if i != j)
        for i in range(n)
    ]

    best_route = None
    best_dist = initial_upper_bound if initial_upper_bound is not None else float("inf")
    complete_routes = 0
    branches_pruned = 0

    def search(
        curr_city: int,
        visited_mask: int,
        count: int,
        current_cost: float,
        current_path: List[int],
    ) -> None:
        nonlocal best_dist, best_route, complete_routes, branches_pruned

        if count == n:
            total_cost = current_cost + distances[curr_city][0]
            complete_routes += 1
            if total_cost < best_dist:
                best_dist = total_cost
                best_route = list(current_path) + [0]
            return

        # Lower bound estimation for remaining unvisited cities
        remaining_lb = sum(
            min_outgoing[i] for i in range(n) if not (visited_mask & (1 << i))
        )

        if current_cost + remaining_lb >= best_dist:
            branches_pruned += 1
            return

        # Branch to unvisited neighbors, sorted by distance for quicker pruning
        unvisited = [j for j in range(n) if not (visited_mask & (1 << j))]
        unvisited.sort(key=lambda j: distances[curr_city][j])

        for nxt in unvisited:
            step_cost = current_cost + distances[curr_city][nxt]
            if step_cost >= best_dist:
                branches_pruned += 1
                continue
            search(
                nxt,
                visited_mask | (1 << nxt),
                count + 1,
                step_cost,
                current_path + [nxt],
            )

    search(0, 1 << 0, 1, 0.0, [0])
    return best_route, best_dist, complete_routes, branches_pruned


def run_branch_and_bound(
    dist_matrix: List[List[float]],
    initial_upper_bound: Optional[float] = None,
) -> Dict:
    """Run Branch and Bound and return benchmark metrics."""
    t_start = time.perf_counter()
    best_route, best_dist, complete_routes, branches_pruned = branch_and_bound(
        dist_matrix,
        initial_upper_bound=initial_upper_bound,
    )
    exec_time = time.perf_counter() - t_start

    return {
        "route": best_route,
        "distance": best_dist,
        "time_sec": exec_time,
        "complete_routes": complete_routes,
        "branches_pruned": branches_pruned,
    }


def main(file_path: str) -> None:
    cities, points = read_cities(file_path)
    distances = build_euclidean_matrix(points)

    # Use Nearest Neighbour to establish a tight initial upper bound
    nn_route, _ = nearest_neighbour(distances)
    nn_distance = route_length(nn_route, distances)

    t0 = time.perf_counter()
    route, best_dist, complete_routes, branches_pruned = branch_and_bound(
        distances,
        initial_upper_bound=nn_distance + 1e-9,
    )
    bb_seconds = time.perf_counter() - t0

    if route is None:
        route = nn_route

    metrics = [
        ("Branch & Bound execution time", f"{bb_seconds:.9f} seconds"),
        ("Initial NN upper bound", f"{nn_distance:,.2f}"),
        ("Complete tours evaluated", f"{complete_routes:,}"),
        ("Subtrees pruned", f"{branches_pruned:,}"),
        ("Theoretical worst-case permutations", f"{math.factorial(len(cities) - 1):,}"),
        ("Time complexity (worst case)", "O((n-1)!)"),
    ]

    save_report(
        file_path,
        cities,
        distances,
        route,
        metrics,
        "branch_and_bound",
        nn_distance,
    )


if __name__ == "__main__":
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Excel file path: ").strip().strip('"')
    )
    main(path)
