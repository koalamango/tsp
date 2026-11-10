"""Animate 2-opt improvements to a nearest-neighbour tour.

Run: python Group_Work/two_opt_visualization.py
Or supply an Excel path. Click the plot to advance each stage.
Excel columns: City, X, Y. Requires matplotlib, openpyxl, numpy and scipy.
"""

import argparse
import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from nearest_neighbour import nearest_neighbour, read_cities, route_length
from two_opt import two_opt
from visualization_window import fit_window_to_screen, wait_for_click


PAD = 20
WINDOW_PARAMETER = 20


class WindowClosed(Exception):
    """Stop the animation when its window is closed."""


def visualize(file_path, initial_route=None):
    """Use an optional closed list of city indices, or build an NN tour."""
    cities, points = read_cities(file_path)
    distances = [[math.dist(a, b) for b in points] for a in points]
    route = (
        nearest_neighbour(distances)[0]
        if initial_route is None else list(initial_route)
    )
    n = len(cities)
    if (len(route) != n + 1 or route[0] != route[-1]
            or sorted(route[:-1]) != list(range(n))):
        raise ValueError("The input route must visit every city index once and return to its start.")
    initial_length = route_length(route, distances)

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
        canvas.annotate(name, (x, y), xytext=(6, 0),
                        textcoords="offset points", va="center", zorder=3)
    canvas.legend(handles=[
        Line2D([], [], color="red", linewidth=2, label="Current tour"),
        Line2D([], [], color="blue", linestyle="--", linewidth=3, label="Remove these edges"),
        Line2D([], [], color="green", linewidth=3, label="Add these edges"),
    ], loc="best")
    tour_lines = []

    def edge(a, b, **style):
        (x1, y1), (x2, y2) = points[a], points[b]
        line, = canvas.plot([x1, x2], [y1, y2], **style)
        return line

    def draw_tour(current_route):
        for line in tour_lines:
            line.remove()
        tour_lines.clear()
        for a, b in zip(current_route, current_route[1:]):
            tour_lines.append(edge(a, b, color="red", linewidth=2, zorder=1))

    def wait():
        if not wait_for_click(figure):
            raise WindowClosed

    def show_move(current_route, i, j, number):
        a, b = current_route[i:i + 2]
        c, d = current_route[j:j + 2]
        old_length = route_length(current_route, distances)
        saving = distances[a][b] + distances[c][d] - distances[a][c] - distances[b][d]
        # Hide the red originals so the dashed removal markers are clear.
        tour_lines[i].set_visible(False)
        tour_lines[j].set_visible(False)
        highlights = [
            edge(a, b, color="blue", linestyle="--", linewidth=3, zorder=2),
            edge(c, d, color="blue", linestyle="--", linewidth=3, zorder=2),
            edge(a, c, color="green", linewidth=3, zorder=2),
            edge(b, d, color="green", linewidth=3, zorder=2),
        ]
        canvas.set_title(
            f"2-opt move {number}: replace two edges and reverse the segment\n"
            f"{old_length:.2f} -> {old_length - saving:.2f} | Saving: {saving:.2f}"
        )
        wait()
        for line in highlights:
            line.remove()
        current_route[i + 1:j + 1] = reversed(current_route[i + 1:j + 1])
        draw_tour(current_route)
        # Keep the replacements green for a full click-controlled stage.
        replacements = [
            edge(a, c, color="green", linewidth=3, zorder=2),
            edge(b, d, color="green", linewidth=3, zorder=2),
        ]
        canvas.set_title(
            f"Move {number} applied: new edges shown in green\n"
            f"{cities[a]} - {cities[c]} and {cities[b]} - {cities[d]} | "
            f"Distance: {route_length(current_route, distances):.2f}"
        )
        wait()
        for line in replacements:
            line.remove()

    draw_tour(route)
    label = "Nearest-neighbour tour" if initial_route is None else "Input tour"
    canvas.set_title(f"{label} | Distance: {initial_length:.2f}")
    figure.tight_layout()
    fit_window_to_screen(figure)
    plt.ion()
    try:
        plt.show()
        wait()
        final_route, checks, passes, moves = two_opt(route, distances, on_move=show_move)
        draw_tour(final_route)
        final_length = route_length(final_route, distances)
        canvas.set_title(
            f"2-opt complete: no improving two-edge swap remains\n"
            f"{initial_length:.2f} -> {final_length:.2f} | {moves} moves"
        )
        print(f"Initial distance: {initial_length:.6f}")
        print(f"Final 2-opt distance: {final_length:.6f}")
        print(f"Accepted moves: {moves} | Swap checks: {checks} | Complete scans: {passes}")
        print("Route: " + " -> ".join(cities[i] for i in final_route))
        print("2-opt finds a local optimum; the global shortest tour is not guaranteed.")
        plt.ioff()
        plt.show()
        return final_route
    except WindowClosed:
        return None
    finally:
        plt.ioff()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename", nargs="?", help="Excel spreadsheet path")
    args = parser.parse_args()
    filename = args.filename or input("Enter the Excel spreadsheet path: ").strip().strip('"')
    visualize(filename)


if __name__ == "__main__":
    main()
