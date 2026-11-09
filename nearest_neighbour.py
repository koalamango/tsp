"""
Author: Richard Clark

Run: py nearest_neighbour.py "C:/path/cities.xlsx"

Requires: py -m pip install openpyxl scipy

Excel columns: City, X, Y.
The first city is the start and finish.
Results are saved as Markdown (.md) in the outputs folder; rerunning replaces the report.
"""
import math
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
from openpyxl import load_workbook
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def read_cities(file_path):
    workbook = load_workbook(file_path, read_only=True, data_only=True)
    try:
        sheet = (
            workbook["Cities"]
            if "Cities" in workbook.sheetnames
            else workbook.worksheets[0]
        )
        rows = iter(sheet.values)
        header = next(rows, ())

        if [str(v).strip().lower() for v in header[:3]] != ["city", "x", "y"]:
            raise ValueError("The first three columns must be City, X, Y.")

        cities, points = [], []

        for row in rows:
            if all(v is None for v in row[:3]):
                continue

            name, x, y = row[:3]

            if name is None or not str(name).strip() or x is None or y is None:
                raise ValueError("Each city needs a name and two coordinates.")

            point = (float(x), float(y))

            if not all(math.isfinite(v) for v in point):
                raise ValueError("Coordinates must be finite numbers.")

            cities.append(str(name))
            points.append(point)

        if len(cities) < 2:
            raise ValueError("At least two cities are required.")

        return cities, points
    finally:
        workbook.close()


def nearest_neighbour(distances):
    """Return a closed route and the number of candidate distances examined."""
    route = [0]
    unvisited = set(range(1, len(distances)))
    examinations = 0

    while unvisited:
        examinations += len(unvisited)
        current = route[-1]

        next_city = min(
            unvisited,
            key=lambda city: (distances[current][city], city),
        )

        route.append(next_city)
        unvisited.remove(next_city)

    return route + [0], examinations


def route_length(route, distances):
    return sum(
        distances[a][b]
        for a, b in zip(route, route[1:])
    )


def exact_route(distances):
    """Find an optimal tour using HiGHS integer programming.

    Each city must have two selected edges. If the selected edges form
    several smaller cycles, forbid those cycles and solve again.

    A connected optimal solution is an optimal TSP tour, within the
    solver's floating-point tolerances.

    There is no time limit. Large problems may take a long time.
    """
    n = len(distances)

    if n == 2:
        return [0, 1, 0]

    edges = [
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
    ]
    costs = np.array([distances[i][j] for i, j in edges])

    degree = lil_matrix((n, len(edges)))

    for k, (i, j) in enumerate(edges):
        degree[i, k] = degree[j, k] = 1

    constraints = [LinearConstraint(degree.tocsc(), 2, 2)]

    while True:
        result = milp(
            costs,
            integrality=np.ones(len(edges)),
            bounds=Bounds(0, 1),
            constraints=constraints,
            options={"mip_rel_gap": 0.0},
        )

        if not result.success:
            raise RuntimeError(
                "Exact optimum not proved: " + result.message
            )

        neighbours = [[] for _ in range(n)]

        for selected, (i, j) in zip(result.x, edges):
            if selected > 0.5:
                neighbours[i].append(j)
                neighbours[j].append(i)

        if any(len(v) != 2 for v in neighbours):
            raise RuntimeError("Exact solver returned an invalid tour.")

        # Find connected components in the selected edges.
        remaining = set(range(n))
        components = []

        while remaining:
            stack = [min(remaining)]
            component = set()

            while stack:
                city = stack.pop()

                if city not in component:
                    component.add(city)
                    stack.extend(
                        v for v in neighbours[city]
                        if v not in component
                    )

            remaining -= component
            components.append(component)

        # A single connected cycle is a complete TSP tour.
        if len(components) == 1:
            route = [0]
            previous, current = -1, 0

            while True:
                nxt = next(
                    v for v in neighbours[current]
                    if v != previous
                )
                route.append(nxt)

                if nxt == 0:
                    return route

                previous, current = current, nxt

        # Add constraints forbidding the smaller cycles.
        for component in components:
            cut = lil_matrix((1, len(edges)))

            for k, (i, j) in enumerate(edges):
                if i in component and j in component:
                    cut[0, k] = 1

            constraints.append(
                LinearConstraint(
                    cut.tocsc(),
                    -np.inf,
                    len(component) - 1,
                )
            )


def save_report(
    file_path,
    cities,
    distances,
    route,
    metrics,
    suffix,
    initial_distance=None,
):
    """Keep exact-reference time separate from heuristic efficiency."""
    length = route_length(route, distances)

    print("Finding and proving the shortest route...")

    start = perf_counter()
    optimum_route = exact_route(distances)
    optimum = route_length(optimum_route, distances)
    exact_seconds = perf_counter() - start

    if optimum > 0:
        percent = f"{100 * length / optimum:.4f}%"
        excess = f"{100 * (length / optimum - 1):.4f}%"
    else:
        percent = excess = "Undefined (optimum is zero)"

    lines = [
        f'# {suffix.replace("_", " ").title()} results',
        "",
        f"**Input:** {Path(file_path).name}",
        "",
        f"**Cities:** {len(cities)} (including the starting city)",
        "",
        "## Route quality",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Final distance | {length:.6f} |",
        f"| Shortest possible distance | {optimum:.6f} |",
        f"| Final distance as % of shortest | {percent} |",
        f"| Distance above optimum | {excess} |",
    ]

    if initial_distance is not None:
        lines.append(
            f"| Initial nearest-neighbour distance | {initial_distance:.6f} |"
        )

    lines += [
        "",
        "100% means optimal; 110% means 10% longer than optimal.",
        "",
        "Distances are straight-line distances in the coordinates' units.",
        "",
        "## Efficiency",
        "",
        "| Measure | Value |",
        "|---|---|",
    ]

    lines += [
        f"| {label} | {value} |"
        for label, value in metrics
    ]

    lines += [
        "",
        "Times are single-run wall-clock measurements and vary by machine.",
        "Heuristic timings exclude Excel loading, matrix construction, "
        "exact search and file writing.",
        "Counters measure the stated search operations, "
        "not every Python operation.",
        "Matrix construction takes O(n^2) time and memory; "
        "route storage uses O(n).",
        "",
        "## Exact reference",
        "",
        f"- Exact-reference time, including model construction: "
        f"{exact_seconds:.6f} seconds.",
        "- Method: HiGHS MILP solver with subtour-elimination cuts.",
        "- Status: optimal to solver numerical tolerances; "
        "requested relative MIP gap = 0.",
        "- Floating-point Euclidean distances are not rounded before solving.",
        "- Exact search is separate from the reported heuristic complexity "
        "and can dominate total runtime.",
        "- No exact algorithm is fastest for every input; "
        "this uses a compiled solver instead of brute force.",
        "",
        "## Final visiting order",
        "",
    ]

    lines += [
        f"{step}. {cities[city]}"
        for step, city in enumerate(route, 1)
    ]

    lines += ["", "## Optimal visiting order", ""]

    lines += [
        f"{step}. {cities[city]}"
        for step, city in enumerate(optimum_route, 1)
    ]

    lines += [
        "",
        "## Method notes",
        "",
        "The first spreadsheet city is the start and end. "
        "Equal NN distances are resolved by input order.",
        "n is the number of cities. For 2-opt, p is the number "
        "of complete scans, including the last scan.",
        "Each scan checks n(n-3)/2 edge pairs for n >= 3. "
        "An accepted segment reversal costs O(n).",
        "2-opt is O(p*n^2), not necessarily O(n^2) overall: "
        "p depends on the input.",
        "",
        "## Solver reference",
        "",
        "https://docs.scipy.org/doc/scipy/reference/generated/"
        "scipy.optimize.milp.html",
        "",
    ]

    spreadsheet = Path(file_path)
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output = outputs_dir / f"{spreadsheet.stem}_{suffix}_results.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Results saved to: {output.resolve()}")


def main(file_path):
    cities, points = read_cities(file_path)
    distances = [
        [math.dist(a, b) for b in points]
        for a in points
    ]

    start = perf_counter()
    route, examinations = nearest_neighbour(distances)
    seconds = perf_counter() - start

    metrics = [
        ("NN execution time", f"{seconds:.9f} seconds"),
        ("NN candidate-distance examinations", f"{examinations:,}"),
        ("NN operation-count formula", "n(n-1)/2"),
        ("NN time complexity", "O(n^2)"),
    ]

    save_report(
        file_path,
        cities,
        distances,
        route,
        metrics,
        "nearest_neighbour",
    )


if __name__ == "__main__":
    path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Excel file path: ").strip().strip('"')
    )
    main(path)