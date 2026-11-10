"""Save a step-by-step nearest-neighbour GIF from the first worksheet.

Run: python nearest_neighbour_gif.py
Optional: python nearest_neighbour_gif.py data/coordinates_10_cities.xlsx
Requires matplotlib, Pillow, openpyxl, numpy and scipy.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
from openpyxl import load_workbook

from nearest_neighbour import build_euclidean_matrix, nearest_neighbour, route_length


ROOT = Path(__file__).resolve().parent


def create_gif(path, output, seconds=1.4):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        sheet_name = sheet.title
        rows = iter(sheet.values)
        header = next(rows, ())
        if [str(v).strip().lower() for v in header[:3]] != ["city", "x", "y"]:
            raise ValueError("The first worksheet must have City, X, Y columns.")
        cities, points = [], []
        import math
        for row in rows:
            if all(value is None for value in row[:3]):
                continue
            name, x, y = row[:3]
            if name is None or not str(name).strip():
                raise ValueError("Each city needs a name.")
            point = (float(x), float(y))
            if not all(math.isfinite(value) for value in point):
                raise ValueError("Coordinates must be finite numbers.")
            cities.append(str(name).strip())
            points.append(point)
    finally:
        workbook.close()
    if len(cities) < 2:
        raise ValueError("At least two cities are required.")

    distances = build_euclidean_matrix(points)
    route, _ = nearest_neighbour(distances)
    # Each move first compares all unvisited cities, then commits the nearest edge.
    frames = [("start", 0)]
    for step in range(len(cities) - 1):
        frames.extend([("compare", step), ("choose", step)])
    frames.extend([("return", len(cities) - 1), ("done", len(cities))])
    frames.extend([("done", len(cities))] * 2)

    fig, ax = plt.subplots(figsize=(11, 8))
    xs, ys = zip(*points)
    pad = max(max(xs) - min(xs), max(ys) - min(ys), 1) * 0.16

    def draw(frame):
        phase, step = frame
        ax.clear()
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_aspect("equal")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.grid(alpha=0.15)
        completed = step + 1 if phase in ("choose", "return") else step
        visited_route = route[:completed + 1]
        current = visited_route[-1]
        visited = set(visited_route)
        for i, (name, point) in enumerate(zip(cities, points)):
            ax.scatter(*point, color="#2563eb" if i in visited else "#9ca3af", s=65, zorder=4)
            ax.annotate(name, point, xytext=(7, 7), textcoords="offset points", fontsize=9)
        for a, b in zip(visited_route, visited_route[1:]):
            ax.annotate("", xy=points[b], xytext=points[a],
                        arrowprops=dict(arrowstyle="->", color="#2563eb", lw=2.3))
        ax.scatter(*points[current], s=180, facecolors="none", edgecolors="#f59e0b", linewidths=3, zorder=5)
        distance = route_length(visited_route, distances)
        if phase == "compare":
            candidates = sorted(set(range(len(cities))) - visited)
            chosen = route[step + 1]
            for candidate in candidates:
                a, b = points[current], points[candidate]
                selected = candidate == chosen
                ax.plot([a[0], b[0]], [a[1], b[1]], "--",
                        color="#16a34a" if selected else "#9ca3af",
                        lw=2 if selected else 1, alpha=0.8)
            choices = sorted(candidates, key=lambda c: (distances[current][c], c))
            detail = "   |   ".join(f"{cities[c]}: {distances[current][c]:.1f}" for c in choices)
            title = f"Step {step + 1}: compare unvisited cities from {cities[current]}"
            subtitle = f"Nearest is {cities[chosen]} ({distances[current][chosen]:.2f})"
        elif phase == "choose":
            title = f"Step {step + 1}: move to the nearest unvisited city"
            subtitle = f"{cities[route[step]]} -> {cities[current]}"
            detail = "Repeat from the new city. Already visited cities are excluded."
        elif phase in ("return", "done"):
            title = "All cities visited: return to the starting city" if phase == "return" else "Nearest-neighbour tour complete"
            subtitle = f"Total distance: {distance:.2f}"
            detail = " -> ".join(cities[c] for c in route)
        else:
            title = f"Start at {cities[0]}"
            subtitle = "At each step, choose the closest city that has not been visited."
            detail = "Dashed lines compare candidates; green highlights the nearest candidate."
        ax.set_title(f"{title}\n{subtitle}", fontsize=13, pad=15)
        fig.suptitle(f"Nearest neighbour | {Path(path).name} | {sheet_name}", fontsize=11)
        ax.legend(handles=[
            Line2D([], [], color="#2563eb", lw=2, label="Chosen route / visited"),
            Line2D([], [], color="#16a34a", linestyle="--", label="Nearest candidate"),
            Line2D([], [], color="#f59e0b", marker="o", linestyle="none", markerfacecolor="none", label="Current city"),
        ], loc="upper right", fontsize=8)
        # Wrap long comparison lists without crowding the plot.
        import textwrap
        footer.set_text(textwrap.fill(detail, width=115) + f"\nDistance travelled: {distance:.2f}")

    footer = fig.text(0.5, 0.03, "", ha="center", va="bottom", fontsize=9)
    fig.subplots_adjust(bottom=0.20, top=0.85)
    animation = FuncAnimation(fig, draw, frames=frames, interval=seconds * 1000, repeat=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        animation.save(output, writer=PillowWriter(fps=1 / seconds), dpi=100)
    finally:
        plt.close(fig)
    print(f"GIF saved to: {output.resolve()}")
    print(f"Tour distance: {route_length(route, distances):.6f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path,
                        default=ROOT / "data" / "coordinates_10_cities.xlsx")
    parser.add_argument("--output", type=Path, help="Output GIF path")
    args = parser.parse_args()
    output = args.output or ROOT / "outputs" / f"{args.file.stem}_nearest_neighbour.gif"
    create_gif(args.file, output)


if __name__ == "__main__":
    main()
