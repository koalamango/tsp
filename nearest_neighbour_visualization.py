"""Animate nearest_neighbour.py using the style of data_visualization.py.

Run from the project folder:
    py Group_Work/nearest_neighbour_visualization.py Data/cities_10_cartesian.xlsx

Omit the filename to enter it interactively. Click the plot to advance each stage.
Requires matplotlib, openpyxl, numpy and scipy.
"""

import argparse
import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from nearest_neighbour import nearest_neighbour, read_cities, route_length
from visualization_window import fit_window_to_screen, wait_for_click


PAD = 20
WINDOW_PARAMETER = 20


def visualize(file_path):
    """Draw candidate connections, then add each chosen edge to the tour."""
    cities, points = read_cities(file_path)
    distances = [[math.dist(a, b) for b in points] for a in points]
    # Use the existing solver, including its input-order tie breaking.
    route, examinations = nearest_neighbour(distances)

    xs, ys = zip(*points)
    width = max(xs) - min(xs) + 2 * PAD
    height = max(ys) - min(ys) + 2 * PAD
    scale = WINDOW_PARAMETER / (width + height)
    figure, canvas = plt.subplots(figsize=(width * scale, height * scale))
    canvas.set_xlim(min(xs) - PAD, max(xs) + PAD)
    canvas.set_ylim(min(ys) - PAD, max(ys) + PAD)
    canvas.set_aspect("equal")

    for name, (x, y) in zip(cities, points):
        canvas.plot(x, y, "o", color="black", zorder=3)
        canvas.annotate(
            name, (x, y), xytext=(6, 0), textcoords="offset points",
            va="center", zorder=3,
        )

    current_dot, = canvas.plot(
        [xs[0]], [ys[0]], "o", color="orange", markersize=10, zorder=4,
    )
    canvas.legend(handles=[
        Line2D([], [], color="red", linewidth=2, label="Chosen route"),
        Line2D([], [], color="gray", linestyle="--", label="Unvisited candidates"),
        Line2D([], [], color="orange", marker="o", linestyle="None", label="Current city"),
    ], loc="best")
    canvas.set_title(f"Nearest neighbour: start at {cities[0]}")
    figure.tight_layout()
    fit_window_to_screen(figure)

    def wait():
        return wait_for_click(figure)

    plt.ion()
    try:
        plt.show()
        if not wait():
            return route

        unvisited = set(range(1, len(cities)))
        total = 0.0
        for step, (current, next_city) in enumerate(zip(route, route[1:]), 1):
            x1, y1 = points[current]
            candidates = []
            if unvisited:
                for candidate in sorted(unvisited):
                    x2, y2 = points[candidate]
                    line, = canvas.plot(
                        [x1, x2], [y1, y2], color="gray", linestyle="--",
                        linewidth=1, alpha=0.5, zorder=0,
                    )
                    candidates.append(line)
                canvas.set_title(
                    f"Step {step}: {cities[current]} considers "
                    f"{len(unvisited)} unvisited cities"
                )
                if not wait():
                    return route

            for line in candidates:
                line.remove()
            x2, y2 = points[next_city]
            canvas.plot([x1, x2], [y1, y2], color="red", linewidth=2, zorder=1)
            current_dot.set_data([x2], [y2])
            total += distances[current][next_city]
            unvisited.discard(next_city)
            action = "Return to start" if step == len(cities) else "Choose nearest"
            canvas.set_title(
                f"Step {step}: {action}: {cities[current]} -> {cities[next_city]}\n"
                f"Edge: {distances[current][next_city]:.2f} | Distance so far: {total:.2f}"
            )
            if not wait():
                return route

        length = route_length(route, distances)
        canvas.set_title(f"Nearest neighbour complete | Total distance: {length:.2f}")
        print("Route: " + " -> ".join(cities[index] for index in route))
        print(f"Total distance: {length:.6f}")
        print(f"Candidate distances examined: {examinations}")
        plt.ioff()
        plt.show()
    finally:
        plt.ioff()
    return route


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename", nargs="?", help="Excel file with City, X, Y columns")
    args = parser.parse_args()
    filename = args.filename or input("Enter the Excel filename: ").strip().strip('"')
    visualize(filename)


if __name__ == "__main__":
    main()
