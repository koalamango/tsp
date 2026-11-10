"""
Author: Richard Clark

Run: python algorithm/heuristics/two_opt.py "data/coordinates_20_cities.xlsx"

This creates its own nearest-neighbour route, then improves it with 2-opt.
It imports shared functions, not saved results, from algorithm.heuristics.nearest_neighbour.
"""
from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from algorithm.heuristics.nearest_neighbour import (
    build_euclidean_matrix,
    read_cities,
    nearest_neighbour,
    route_length,
    save_report,
)


def two_opt(route, distances, on_move=None):
    """Best-improvement 2-opt for symmetric distances."""
    route = route.copy()
    n = len(route) - 1
    checks = passes = moves = 0

    while True:
        passes += 1
        best_change = -1e-10
        best_pair = None

        for i in range(n - 2):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue  # These edges share the starting city.

                a, b = route[i], route[i + 1]
                c, d = route[j], route[j + 1]

                change = (
                    distances[a][c] + distances[b][d]
                    - distances[a][b] - distances[c][d]
                )
                checks += 1

                if change < best_change:
                    best_change = change
                    best_pair = (i, j)

        if best_pair is None:
            return route, checks, passes, moves

        i, j = best_pair
        moves += 1
        if on_move is not None:
            on_move(route.copy(), i, j, moves)
        route[i + 1:j + 1] = reversed(route[i + 1:j + 1])


def main(file_path):
    cities, points = read_cities(file_path)
    distances = build_euclidean_matrix(points)

    start = perf_counter()
    route, examinations = nearest_neighbour(distances)
    nn_seconds = perf_counter() - start

    initial_distance = route_length(route, distances)

    start = perf_counter()
    route, checks, passes, moves = two_opt(route, distances)
    opt_seconds = perf_counter() - start

    metrics = [
        ("NN execution time", f"{nn_seconds:.9f} seconds"),
        ("2-opt refinement time", f"{opt_seconds:.9f} seconds"),
        (
            "Combined heuristic time",
            f"{nn_seconds + opt_seconds:.9f} seconds",
        ),
        ("NN candidate-distance examinations", f"{examinations:,}"),
        ("2-opt candidate-swap examinations", f"{checks:,}"),
        ("2-opt complete scans (p)", f"{passes:,}"),
        ("Accepted 2-opt moves", f"{moves:,}"),
        ("NN operation-count formula", "n(n-1)/2"),
        ("2-opt swap-count formula (n >= 3)", "p*n(n-3)/2"),
        ("NN time complexity", "O(n^2)"),
        ("2-opt time complexity", "O(p*n^2)"),
        ("Combined time complexity", "O(n^2 + p*n^2)"),
    ]

    save_report(
        file_path,
        cities,
        distances,
        route,
        metrics,
        "two_opt",
        initial_distance,
    )


if __name__ == "__main__":
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Excel file path: ").strip().strip('"')
    )
    main(path)