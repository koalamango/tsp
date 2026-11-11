# ============================================================
# Author: Tyrone Sequeira
# CHRISTOFIDES ALGORITHM FOR THE TRAVELLING SALESMAN PROBLEM
# CSV VERSION - NO PANDAS OR NUMPY REQUIRED
# ============================================================

import csv
import math
import matplotlib.pyplot as plt


# ============================================================
# STEP 1: LOAD CITY DATA FROM CSV
# ============================================================

file_path = "cities_10_cartesian.csv"

cities = []
x_coordinates = []
y_coordinates = []

with open(file_path, "r", newline="", encoding="utf-8-sig") as file:

    reader = csv.DictReader(file)

    for row in reader:

        cities.append(row["City"])

        x_coordinates.append(float(row["X"]))

        y_coordinates.append(float(row["Y"]))


number_of_cities = len(cities)

print("\nNUMBER OF CITIES:", number_of_cities)


# ============================================================
# STEP 2: CREATE EUCLIDEAN DISTANCE MATRIX
# ============================================================

distance_matrix = []

for i in range(number_of_cities):

    row = []

    for j in range(number_of_cities):

        dx = x_coordinates[i] - x_coordinates[j]

        dy = y_coordinates[i] - y_coordinates[j]

        distance = math.sqrt(dx**2 + dy**2)

        row.append(distance)

    distance_matrix.append(row)


# ============================================================
# STEP 3: PRIM'S MINIMUM SPANNING TREE
# ============================================================

def prim_mst():

    visited = [False] * number_of_cities

    visited[0] = True

    mst_edges = []

    for _ in range(number_of_cities - 1):

        minimum_distance = float("inf")

        best_edge = None

        for i in range(number_of_cities):

            if visited[i]:

                for j in range(number_of_cities):

                    if not visited[j]:

                        if distance_matrix[i][j] < minimum_distance:

                            minimum_distance = distance_matrix[i][j]

                            best_edge = (i, j)

        if best_edge is None:
            raise ValueError("Unable to construct the MST.")

        u, v = best_edge

        mst_edges.append((u, v))

        visited[v] = True

    return mst_edges


mst_edges = prim_mst()


# ============================================================
# STEP 4: FIND ODD DEGREE VERTICES
# ============================================================

degree = [0] * number_of_cities

for u, v in mst_edges:

    degree[u] += 1

    degree[v] += 1


odd_vertices = []

for i in range(number_of_cities):

    if degree[i] % 2 == 1:

        odd_vertices.append(i)


# ============================================================
# STEP 5: MINIMUM WEIGHT PERFECT MATCHING
# ============================================================

def minimum_matching(vertices):

    if not vertices:

        return [], 0

    first = vertices[0]

    best_cost = float("inf")

    best_matching = []

    for i in range(1, len(vertices)):

        second = vertices[i]

        remaining = vertices[1:i] + vertices[i + 1:]

        matching, cost = minimum_matching(remaining)

        total_cost = distance_matrix[first][second] + cost

        if total_cost < best_cost:

            best_cost = total_cost

            best_matching = [(first, second)] + matching

    return best_matching, best_cost


matching_edges, matching_cost = minimum_matching(odd_vertices)


# ============================================================
# STEP 6: COMBINE MST AND MATCHING EDGES
# ============================================================

multigraph_edges = mst_edges + matching_edges


# ============================================================
# STEP 7: CREATE EULERIAN CIRCUIT
# ============================================================

def eulerian_circuit(edges):

    graph = [[] for _ in range(number_of_cities)]

    for edge_id, (u, v) in enumerate(edges):

        graph[u].append((v, edge_id))

        graph[v].append((u, edge_id))

    used = set()

    stack = [0]

    circuit = []

    while stack:

        current = stack[-1]

        while graph[current] and graph[current][-1][1] in used:

            graph[current].pop()

        if graph[current]:

            neighbour, edge_id = graph[current].pop()

            if edge_id not in used:

                used.add(edge_id)

                stack.append(neighbour)

        else:

            circuit.append(stack.pop())

    return circuit[::-1]


euler_tour = eulerian_circuit(multigraph_edges)


# ============================================================
# STEP 8: SHORTCUT REPEATED CITIES
# ============================================================

final_route = []

visited = set()

for city in euler_tour:

    if city not in visited:

        final_route.append(city)

        visited.add(city)


# Return to the starting city

final_route.append(final_route[0])


# ============================================================
# STEP 9: CALCULATE FINAL ROUTE DISTANCE
# ============================================================

total_distance = 0

for i in range(len(final_route) - 1):

    u = final_route[i]

    v = final_route[i + 1]

    total_distance += distance_matrix[u][v]


# ============================================================
# STEP 10: DISPLAY RESULTS
# ============================================================

print("\n======================================")

print("CHRISTOFIDES ALGORITHM RESULTS")

print("======================================")

print("\nMinimum Spanning Tree:")

for u, v in mst_edges:

    print(cities[u], "to", cities[v],
          "=", round(distance_matrix[u][v], 2))


print("\nOdd Degree Vertices:")

for vertex in odd_vertices:

    print(cities[vertex])


print("\nMinimum Weight Matching:")

for u, v in matching_edges:

    print(cities[u], "to", cities[v],
          "=", round(distance_matrix[u][v], 2))


print("\nEulerian Circuit:")

print(" -> ".join(cities[i] for i in euler_tour))


print("\nFinal Christofides Route:")

print(" -> ".join(cities[i] for i in final_route))


print("\nTotal Route Distance:")

print(round(total_distance, 2))


# ============================================================
# STEP 11: VISUALISATION FUNCTION
# ============================================================

def draw_edges(edges, title, filename):

    fig, ax = plt.subplots(figsize=(10, 8))

    for u, v in edges:

        ax.plot(
            [x_coordinates[u], x_coordinates[v]],
            [y_coordinates[u], y_coordinates[v]],
            marker="o"
        )

    for i in range(number_of_cities):

        ax.annotate(
            cities[i],
            (x_coordinates[i], y_coordinates[i]),
            xytext=(5, 5),
            textcoords="offset points"
        )

    ax.set_title(title)

    ax.set_xlabel("X Coordinate")

    ax.set_ylabel("Y Coordinate")

    ax.grid(True)

    ax.set_aspect("equal", adjustable="datalim")

    fig.tight_layout()

    fig.savefig(filename, dpi=300)

    plt.show()

    plt.close(fig)


# ============================================================
# STEP 12: VISUALISATION 1 - MINIMUM SPANNING TREE
# ============================================================

draw_edges(
    mst_edges,
    "Christofides - Minimum Spanning Tree",
    "Christofides_MST.png"
)


# ============================================================
# STEP 13: VISUALISATION 2 - MST PLUS MATCHING
# ============================================================

draw_edges(
    multigraph_edges,
    "Christofides - MST Plus Minimum Matching",
    "Christofides_MST_Matching.png"
)


# ============================================================
# STEP 14: VISUALISATION 3 - FINAL ROUTE
# ============================================================

fig, ax = plt.subplots(figsize=(10, 8))

for i in range(len(final_route) - 1):

    u = final_route[i]

    v = final_route[i + 1]

    ax.annotate(
        "",
        xy=(x_coordinates[v], y_coordinates[v]),
        xytext=(x_coordinates[u], y_coordinates[u]),
        arrowprops=dict(arrowstyle="->")
    )

    midpoint_x = (x_coordinates[u] + x_coordinates[v]) / 2

    midpoint_y = (y_coordinates[u] + y_coordinates[v]) / 2

    ax.text(
        midpoint_x,
        midpoint_y,
        str(i + 1)
    )


for i in range(number_of_cities):

    ax.scatter(x_coordinates[i], y_coordinates[i])

    ax.annotate(
        cities[i],
        (x_coordinates[i], y_coordinates[i]),
        xytext=(5, 5),
        textcoords="offset points"
    )


ax.set_title("Christofides - Final TSP Route")

ax.set_xlabel("X Coordinate")

ax.set_ylabel("Y Coordinate")

ax.grid(True)

ax.set_aspect("equal", adjustable="datalim")

fig.tight_layout()

fig.savefig("Christofides_Final_Route.png", dpi=300)

plt.show()

plt.close(fig)


print("\nAll three visualisations have been saved successfully.")
