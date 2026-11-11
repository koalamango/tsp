"""
Author: Richard Clark2-opt variant of tsp_loader for all sheets in a coordinate workbook.

Run: python tsp_loader_two_opt.py [--runs 10]
Prints results and saves a Markdown report in outputs/.
"""
from __future__ import annotations

import argparse
import math
import statistics
from pathlib import Path
from time import perf_counter

from openpyxl import load_workbook

from nearest_neighbour import (
    build_euclidean_matrix,
    exact_route,
    nearest_neighbour,
    route_length,
)
from tsp_utils import markdown_table
from two_opt import two_opt


ROOT = Path(__file__).resolve().parent


def load_sheets(path):
    """Read every worksheet, validating City, X, Y coordinate data."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        datasets = []
        for sheet in workbook:
            rows = iter(sheet.values)
            header = next(rows, ())
            if [str(v).strip().lower() for v in header[:3]] != ["city", "x", "y"]:
                raise ValueError(f"{sheet.title}: first three columns must be City, X, Y.")
            cities, points = [], []
            for row in rows:
                if all(v is None for v in row[:3]):
                    continue
                name, x, y = row[:3]
                if name is None or not str(name).strip() or x is None or y is None:
                    raise ValueError(f"{sheet.title}: each city needs a name and two coordinates.")
                point = (float(x), float(y))
                if not all(math.isfinite(v) for v in point):
                    raise ValueError(f"{sheet.title}: coordinates must be finite numbers.")
                cities.append(str(name).strip())
                points.append(point)
            if len(cities) < 2:
                raise ValueError(f"{sheet.title}: at least two cities are required.")
            datasets.append((sheet.title, cities, build_euclidean_matrix(points)))
        if not datasets:
            raise ValueError("The workbook contains no worksheets.")
        return datasets
    finally:
        workbook.close()


def benchmark_sheet(name, cities, distances, runs):
    """Time NN construction plus 2-opt; compute the exact reference separately."""
    optimum = route_length(exact_route(distances), distances)

    def solve():
        initial_route, _ = nearest_neighbour(distances)
        return two_opt(initial_route, distances)[0]

    solve()  # Untimed warm-up, matching tsp_loader.
    times = []
    for _ in range(runs):
        start = perf_counter()
        route = solve()
        times.append(perf_counter() - start)
    distance = route_length(route, distances)
    gap = max(0.0, (distance / optimum - 1) * 100) if optimum > 0 else None
    return name, distance, statistics.fmean(times), optimum, gap


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("runs must be at least 1")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=positive_int, default=10,
                        help="Timed NN + 2-opt runs per worksheet (default: 10)")
    args = parser.parse_args()
    entered_path = input("Excel file path (or filename in data/): ").strip().strip('\"').strip("'")
    if not entered_path:
        parser.error("Please enter an Excel file path.")
    path = Path(entered_path).expanduser()
    if not path.is_file() and not path.is_absolute():
        path = ROOT / "data" / path
    if not path.is_file():
        parser.error(f"Excel file not found: {entered_path}")
    try:
        datasets = load_sheets(path)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    results = []
    for index, dataset in enumerate(datasets, 1):
        print(f"Running data set {index} ({dataset[0]}, {len(dataset[1])} cities)...", flush=True)
        results.append(benchmark_sheet(*dataset, args.runs))

    def row(name, distance, seconds, optimum, gap):
        return [name, f"{distance:.6f}", f"{seconds:.9f}", f"{optimum:.6f}",
                f"{gap:.4f}%" if gap is not None else "Undefined (zero optimum)"]

    rows = [row(f"data set {index}", *result[1:])
            for index, result in enumerate(results, 1)]
    averages = [statistics.fmean(result[i] for result in results) for i in (1, 2, 3)]
    # A mean of sheet percentages, rather than a ratio of mean distances.
    average_gap = (statistics.fmean(result[4] for result in results)
                   if all(result[4] is not None for result in results) else None)
    rows.append(row(f"Average ({len(results)} data sets)", *averages, average_gap))
    report = "\n".join([
        f"# 2-Opt (from Nearest Neighbour): {path.stem}", "",
        f"Input: {path.name}. Worksheets: {len(results)}.", "",
        *[f"- data set {index}: {name} ({len(cities)} cities)"
          for index, (name, cities, _) in enumerate(datasets, 1)], "",
        markdown_table(
            ["Data set", "2-opt distance", "Mean NN + 2-opt time (seconds)",
             "Optimal distance", "Distance above optimum"], rows), "",
        f"Time is the mean of {args.runs} timed runs per worksheet after one warm-up.",
        "Timing includes nearest-neighbour starting-tour construction and 2-opt refinement; "
        "it excludes Excel loading, "
        "distance-matrix construction, route evaluation and exact solving.",
        "The first city is the start and finish; ties follow input order.",
        "Distances use unrounded Euclidean coordinates. Optima are computed separately "
        "using the existing exact MILP solver.",
        "Percentage above optimum = 100 * (2-opt distance / optimal distance - 1).",
        "The final row is the arithmetic mean of all worksheet results, "
        "including their individual percentages. A zero optimum makes the "
        "percentage and its overall average undefined.", "",
    ])
    output = ROOT / "outputs" / f"{path.stem}_two_opt_summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    print(f"Results saved to: {output}")


if __name__ == "__main__":
    main()
