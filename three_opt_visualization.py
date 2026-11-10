"""Click through 3-opt improvements to a nearest-neighbour tour.

Run: python Group_Work/three_opt_visualization.py
Optionally supply an Excel filename and --start-from two-opt.
Excel columns: City, X, Y. Requires matplotlib, openpyxl, numpy and scipy.
"""

import argparse
import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from nearest_neighbour import nearest_neighbour, read_cities, route_length
from three_opt import three_opt
from two_opt import two_opt
from visualization_window import fit_window_to_screen, wait_for_click


PAD = 20
WINDOW_PARAMETER = 20


class WindowClosed(Exception):
    """Stop when the visualization window closes."""


def visualize(file_path, initial_route=None, start_from="nearest-neighbour"):
    """Animate accepted moves; optional initial_route is a closed index list."""
    cities, points = read_cities(file_path)
    distances = [[math.dist(a, b) for b in points] for a in points]
    if start_from not in ("nearest-neighbour", "two-opt"):
        raise ValueError("start_from must be nearest-neighbour or two-opt")
    route = nearest_neighbour(distances)[0] if initial_route is None else list(initial_route)
    n = len(cities)
    if (len(route) != n + 1 or route[0] != route[-1]
            or sorted(route[:-1]) != list(range(n))):
        raise ValueError("The route must visit every city index once and return to its start.")
    # The existing 3-opt solver anchors its closed tours at city index 0.
    tour = route[:-1]
    start = tour.index(0)
    tour = tour[start:] + tour[:start]
    route = tour + [0]
    label = "Nearest-neighbour tour" if initial_route is None else "Input tour"
    if start_from == "two-opt":
        route = two_opt(route, distances)[0]
        label = "2-opt tour"
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
        canvas.annotate(name, (x, y), xytext=(6, 0), textcoords="offset points",
                        va="center", zorder=3)
    canvas.legend(handles=[
        Line2D([], [], color="red", linewidth=2, label="Current tour"),
        Line2D([], [], color="blue", linestyle="--", linewidth=3, label="Remove these edges"),
        Line2D([], [], color="green", linewidth=3, label="New edges"),
    ], loc="best")
    lines = []

    def edges(current):
        return {tuple(sorted((a, b))) for a, b in zip(current, current[1:])}

    def draw_edge(pair, **style):
        (x1, y1), (x2, y2) = (points[i] for i in pair)
        line, = canvas.plot([x1, x2], [y1, y2], **style)
        lines.append(line)

    def draw(current, removed=(), added=()):
        for line in lines:
            line.remove()
        lines.clear()
        for pair in sorted(edges(current) - set(removed)):
            draw_edge(pair, color="red", linewidth=2, zorder=1)
        for pair in sorted(removed):
            draw_edge(pair, color="blue", linestyle="--", linewidth=3, zorder=2)
        for pair in sorted(added):
            draw_edge(pair, color="green", linewidth=3, zorder=2)

    def wait():
        if not wait_for_click(figure):
            raise WindowClosed

    def show_move(before, after, number):
        removed = edges(before) - edges(after)
        added = edges(after) - edges(before)
        old_length = route_length(before, distances)
        new_length = route_length(after, distances)
        draw(before, removed, added)
        canvas.set_title(
            f"3-opt move {number}: replace {len(removed)} edges\n"
            f"{old_length:.2f} -> {new_length:.2f} | Saving: {old_length - new_length:.2f}"
        )
        wait()
        draw(after, added=added)
        canvas.set_title(
            f"Move {number} applied: new edges shown in green\nDistance: {new_length:.2f}"
        )
        wait()

    draw(route)
    canvas.set_title(f"{label} | Distance: {initial_length:.2f}")
    figure.tight_layout()
    fit_window_to_screen(figure)
    plt.ion()
    try:
        plt.show()
        wait()
        final, checks, passes, moves = three_opt(route, distances, on_move=show_move)
        draw(final)
        length = route_length(final, distances)
        canvas.set_title(
            f"3-opt complete: no improving reconnection remains\n"
            f"{initial_length:.2f} -> {length:.2f} | {moves} moves"
        )
        print(f"Initial distance: {initial_length:.6f}")
        print(f"Final 3-opt distance: {length:.6f}")
        print(f"Accepted moves: {moves} | Reconnection checks: {checks} | Passes: {passes}")
        print("Route: " + " -> ".join(cities[i] for i in final))
        print("Includes 2-opt-equivalent moves. A global optimum is not guaranteed.")
        plt.ioff()
        plt.show()
        return final
    except WindowClosed:
        return None
    finally:
        plt.ioff()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename", nargs="?", help="Excel spreadsheet path")
    parser.add_argument("--start-from", choices=["nearest-neighbour", "two-opt"],
                        default="nearest-neighbour", help="Initial tour for 3-opt")
    args = parser.parse_args()
    filename = args.filename or input("Enter the Excel spreadsheet path: ").strip().strip('"')
    visualize(filename, start_from=args.start_from)


if __name__ == "__main__":
    main()
