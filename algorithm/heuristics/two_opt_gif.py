"""Animate best-improvement 2-opt on the first worksheet of a coordinate workbook.

Run: python two_opt_gif.py
Optional: python two_opt_gif.py data/coordinates_10_cities.xlsx --output outputs/demo.gif
Requires matplotlib, Pillow, openpyxl, numpy and scipy.
"""
import argparse
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
from openpyxl import load_workbook

from nearest_neighbour import build_euclidean_matrix, nearest_neighbour, route_length
from two_opt import two_opt

ROOT = Path(__file__).resolve().parent


def read_first_sheet(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        rows = iter(sheet.values)
        header = next(rows, ())
        if [str(v).strip().lower() for v in header[:3]] != ["city", "x", "y"]:
            raise ValueError("The first worksheet must have City, X, Y columns.")
        cities, points = [], []
        for row in rows:
            if all(v is None for v in row[:3]):
                continue
            name, x, y = row[:3]
            if name is None or not str(name).strip():
                raise ValueError("Each city needs a name.")
            point = (float(x), float(y))
            if not all(math.isfinite(v) for v in point):
                raise ValueError("Coordinates must be finite numbers.")
            cities.append(str(name).strip())
            points.append(point)
        if len(cities) < 2:
            raise ValueError("At least two cities are required.")
        return sheet.title, cities, points
    finally:
        workbook.close()


def trace_swaps(initial, distances):
    """Mirror two_opt's scan order, best-improvement rule and tolerance."""
    route = initial.copy()
    frames = [("start", route.copy(), None, 0, 0.0)]
    moves = 0
    n = len(route) - 1
    while True:
        best_change, pair = -1e-10, None
        for i in range(n - 2):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                a, b, c, d = route[i], route[i + 1], route[j], route[j + 1]
                change = distances[a][c] + distances[b][d] - distances[a][b] - distances[c][d]
                if change < best_change:
                    best_change, pair = change, (i, j)
        if pair is None:
            frames.append(("done", route.copy(), None, moves, 0.0))
            break
        moves += 1
        frames.append(("swap", route.copy(), pair, moves, -best_change))
        i, j = pair
        route[i + 1:j + 1] = reversed(route[i + 1:j + 1])
        frames.append(("improved", route.copy(), None, moves, -best_change))
    if route != two_opt(initial, distances)[0]:
        raise RuntimeError("Animation trace differs from the existing 2-opt solver.")
    return frames


def create_gif(path, output, seconds=1.8):
    sheet, cities, points = read_first_sheet(path)
    distances = build_euclidean_matrix(points)
    initial, _ = nearest_neighbour(distances)
    frames = trace_swaps(initial, distances)
    initial_distance = route_length(initial, distances)
    fig, ax = plt.subplots(figsize=(11, 8))
    footer = fig.text(0.5, 0.03, "", ha="center", va="bottom", fontsize=9)
    fig.suptitle(f"2-opt | {Path(path).name} | {sheet}", fontsize=11)
    fig.subplots_adjust(bottom=0.20, top=0.85)
    xs, ys = zip(*points)
    pad = max(max(xs) - min(xs), max(ys) - min(ys), 1) * 0.16

    def draw(frame):
        phase, route, pair, move, saving = frame
        ax.clear()
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_aspect("equal")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.grid(alpha=0.15)
        for k, (a, b) in enumerate(zip(route, route[1:])):
            removed = pair is not None and k in pair
            ax.plot([points[a][0], points[b][0]], [points[a][1], points[b][1]],
                    color="#dc2626" if removed else "#2563eb",
                    linestyle="--" if removed else "-", lw=2.5, zorder=2)
        if pair is not None:
            i, j = pair
            for a, b in [(route[i], route[j]), (route[i + 1], route[j + 1])]:
                ax.plot([points[a][0], points[b][0]], [points[a][1], points[b][1]],
                        color="#16a34a", linestyle="--", lw=2.5, zorder=3)
        ax.scatter(xs, ys, s=65, color="#2563eb", zorder=4)
        ax.scatter(*points[0], s=180, facecolors="none", edgecolors="#f59e0b", linewidths=3, zorder=5)
        for name, point in zip(cities, points):
            ax.annotate(name, point, xytext=(7, 7), textcoords="offset points", fontsize=9)
        distance = route_length(route, distances)
        if phase == "start":
            title = "Start with the nearest-neighbour tour"
            detail = "Scan all eligible pairs of edges and choose the swap with the largest distance reduction."
        elif phase == "swap":
            title = f"Swap {move}: replace red edges with green edges"
            detail = f"Reverse the route segment between the cuts. This saves {saving:.2f} distance units."
        elif phase == "improved":
            title = f"Swap {move} applied: shorter tour"
            detail = "Scan edge pairs again to find the next best improvement."
        else:
            title = "Finished: no improving 2-opt swap remains"
            detail = (f"Accepted swaps: {move}. Total saving: {initial_distance - distance:.2f}. "
                      "This is a 2-opt local optimum; it need not be the global optimum.")
        ax.set_title(f"{title}\nTour distance: {distance:.2f}", fontsize=13, pad=15)
        footer.set_text(textwrap.fill(detail, 115) + "\n" + textwrap.fill(" -> ".join(cities[c] for c in route), 115))
        ax.legend(handles=[
            Line2D([], [], color="#2563eb", lw=2, label="Current tour"),
            Line2D([], [], color="#dc2626", linestyle="--", label="Remove these edges"),
            Line2D([], [], color="#16a34a", linestyle="--", label="Add these edges"),
            Line2D([], [], color="#f59e0b", marker="o", linestyle="none", markerfacecolor="none", label="Start / finish"),
        ], loc="upper right", fontsize=8)

    animation = FuncAnimation(fig, draw, frames=frames + [frames[-1]] * 2,
                              interval=seconds * 1000, repeat=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        animation.save(output, writer=PillowWriter(fps=1 / seconds), dpi=100)
    finally:
        plt.close(fig)
    print(f"GIF saved to: {output.resolve()}")
    print(f"Distance: {initial_distance:.6f} -> {route_length(frames[-1][1], distances):.6f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path,
                        default=ROOT / "data" / "coordinates_10_cities.xlsx")
    parser.add_argument("--output", type=Path, help="Output GIF path")
    args = parser.parse_args()
    create_gif(args.file, args.output or ROOT / "outputs" / f"{args.file.stem}_two_opt.gif")


if __name__ == "__main__":
    main()
