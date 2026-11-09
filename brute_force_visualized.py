"""
Author: Oshanda Hembathanthrige
"""

import itertools
import math
import time
import pandas as pd
import matplotlib.pyplot as plt

# Time between iterations
ITERATION_DELAY = 0


# 1. Read the Excel distance matrix
def load_distance(path, sheet_name=0):

    df = pd.read_excel(path, sheet_name=sheet_name, index_col=0)

    df.columns = [str(c).strip() for c in df.columns]
    df.index = [str(i).strip() for i in df.index]

    if set(df.columns) != set(df.index):
        raise ValueError("Row and column city names don't match")

    cities = list(df.columns)
    distances = {city: {} for city in cities}

    for a in cities:
        for b in cities:

            value = df.loc[a, b]

            if a == b or pd.isna(value):
                continue

            d = float(value)

            if d.is_integer():
                d = int(d)

            if b in distances[a] and distances[a][b] != d:
                raise ValueError(f"Conflict for {a}-{b}")

            distances[a][b] = d
            distances[b][a] = d

    return cities, distances


# 2. Arrange cities equally around a circle
def create_visualisation(cities):

    number_of_cities = len(cities)
    positions = {}

    for i, city in enumerate(cities):

        angle = math.pi / 2 - (
            2 * math.pi * i / number_of_cities
        )

        x = math.cos(angle)
        y = math.sin(angle)

        positions[city] = (x, y)

    plt.ion()

    fig, ax = plt.subplots(figsize=(9, 9))

    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")

    # Draw all nodes
    for city, (x, y) in positions.items():

        ax.scatter(x, y, s=650, zorder=3)

        ax.text(
            x * 1.13,
            y * 1.13,
            city,
            ha="center",
            va="center",
            fontsize=10
        )

    # Route line
    route_line, = ax.plot(
        [],
        [],
        linewidth=2.5,
        zorder=2
    )

    # Iteration information
    info_text = ax.text(
        0.02,
        0.02,
        "",
        transform=ax.transAxes,
        fontsize=11,
        va="bottom"
    )

    fig.tight_layout()
    plt.show(block=False)

    return fig, ax, positions, route_line, info_text


# 3. Calculate the distance of a complete route
def calculate_route_distance(route, distances):

    total = 0

    for i in range(len(route) - 1):

        from_city = route[i]
        to_city = route[i + 1]

        total += distances[from_city][to_city]

    return total


# 4. Draw the current route
def display_route(
    route,
    distance,
    iteration,
    total_iterations,
    positions,
    route_line,
    info_text,
    fig
):

    x_values = [
        positions[city][0] for city in route
    ]

    y_values = [
        positions[city][1] for city in route
    ]

    # Update connecting lines
    route_line.set_data(x_values, y_values)

    # Update iteration information
    info_text.set_text(
        f"Iteration: {iteration:,} / {total_iterations:,}\n"
        f"Current route distance: {distance:,.2f}"
    )

    fig.canvas.draw_idle()
    fig.canvas.flush_events()

    # Wait 0.1 seconds
    plt.pause(ITERATION_DELAY)


# 5. Brute-force search
def brute_force_search(cities, distances, start_city=None, visualize=False):

    if start_city is None:
        start_city = cities[0]

    if start_city not in cities:
        raise ValueError(
            f"Starting city '{start_city}' was not found."
        )

    other_cities = [
        city for city in cities if city != start_city
    ]

    # Check all distances exist
    for a in cities:
        for b in cities:

            if a != b and b not in distances[a]:

                raise ValueError(
                    f"Missing distance between {a} and {b}"
                )

    # Initialise best route
    best_route = None
    min_distance = float("inf")

    # Calculate total number of permutations
    total_iterations = math.factorial(len(other_cities))

    # Create visualisation if enabled
    if visualize:
        fig, ax, positions, route_line, info_text = (
            create_visualisation(cities)
        )

        print(f"Total routes to check: {total_iterations:,}")
        print("Close the visualisation window to stop the program.")

    # Brute-force search
    for iteration, perm in enumerate(
        itertools.permutations(other_cities),
        start=1
    ):

        # Construct complete route
        current_route = (
            [start_city] + list(perm) + [start_city]
        )

        # Calculate total distance
        current_distance = calculate_route_distance(
            current_route,
            distances
        )

        # Update shortest route
        if current_distance < min_distance:

            min_distance = current_distance
            best_route = current_route.copy()

        if visualize:
            # Visualise current iteration
            display_route(
                current_route,
                current_distance,
                iteration,
                total_iterations,
                positions,
                route_line,
                info_text,
                fig
            )

            # Stop if window is closed
            if not plt.fignum_exists(fig.number):

                print("Visualisation window closed. Search stopped early.")
                break

    # Display optimal route if visualising
    if visualize:
        if best_route is not None:

            best_x = [
                positions[city][0] for city in best_route
            ]

            best_y = [
                positions[city][1] for city in best_route
            ]

            route_line.set_data(best_x, best_y)
            route_line.set_linewidth(4)

            info_text.set_text(
                f"OPTIMAL ROUTE\n"
                f"{' -> '.join(best_route)}\n"
                f"Minimum distance: {min_distance:,.2f}"
            )

            ax.set_title(
                "Brute Force TSP - Optimal Route",
                fontsize=14
            )

            fig.canvas.draw_idle()
            fig.canvas.flush_events()

            print("\nOptimal Route:")
            print(" -> ".join(best_route))

            print(f"Minimum Distance: {min_distance} miles")

            plt.ioff()
            plt.show()

        else:
            plt.close(fig)

    return best_route, min_distance, total_iterations


def dict_from_matrix(cities, dist_matrix):
    """Convert an n x n numeric distance matrix into a nested city-name dictionary."""
    return {
        c1: {c2: dist_matrix[i][j] for j, c2 in enumerate(cities) if i != j}
        for i, c1 in enumerate(cities)
    }


def run_brute_force(cities, dist_matrix):
    """Run an exact brute-force search and return benchmark metrics with integer route indices."""
    distances = dict_from_matrix(cities, dist_matrix)
    city_to_idx = {city: idx for idx, city in enumerate(cities)}

    t_start = time.perf_counter()
    best_route_names, min_dist, total_permutations = brute_force_search(
        cities,
        distances,
        start_city=cities[0],
        visualize=False,
    )
    exec_time = time.perf_counter() - t_start

    best_route = [city_to_idx[name] for name in best_route_names] if best_route_names else None

    return {
        "route": best_route,
        "distance": min_dist,
        "time_sec": exec_time,
        "permutations": total_permutations,
    }


if __name__ == "__main__":
    # Load Excel file
    filename = input("Enter the Excel filename: ").strip().strip('"')

    cities, distances = load_distance(filename)

    brute_force_search(
        cities,
        distances,
        start_city="London",
        visualize=True
    )

