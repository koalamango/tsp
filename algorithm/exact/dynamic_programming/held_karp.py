import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]

# Read an Excel sheet with columns (Location, X, Y). Returns (coordinates, cities, distances), decimals=0 for easy computation.
def load_distances(path, sheet_name, decimals=0):
    try:
        data_frame = pd.read_excel(path, sheet_name=sheet_name)
    except FileNotFoundError:
        raise FileNotFoundError(f"File '{path}' not found. Check the name and folder, then try again.")
    # Remove completely empty rows
    data_frame = data_frame.dropna(how="all")
    # Check that every row has a name
    if data_frame[data_frame.columns[0]].isna().any():
        raise ValueError("A row without a name")
    # Remove empty spaces from city names (Ex: " Canary wharf " -> "Canary wharf")
    data_frame[data_frame.columns[0]] = data_frame[data_frame.columns[0]].astype(str).str.strip()
    # Check for duplicate city names
    if data_frame[data_frame.columns[0]].duplicated().any():
        dupes = list(data_frame.loc[data_frame[data_frame.columns[0]].duplicated(), data_frame.columns[0]])
        raise ValueError(f"Duplicate locations: {dupes}")
    # Check for different cities sharing the same X, Y position
    same_position = data_frame[data_frame.duplicated(subset=[data_frame.columns[1], data_frame.columns[2]], keep=False)]
    if not same_position.empty:
        raise ValueError("Cities with the same X, Y: " + ", ".join(f"{row[0]} ({row[1]}, {row[2]})" for row in same_position.values))
    # Convert X and Y to numbers and text or empty cells are reported
    data_frame[data_frame.columns[1]] = pd.to_numeric(data_frame[data_frame.columns[1]], errors="coerce")
    data_frame[data_frame.columns[2]] = pd.to_numeric(data_frame[data_frame.columns[2]], errors="coerce")
    bad = data_frame[data_frame[data_frame.columns[1]].isna() | data_frame[data_frame.columns[2]].isna()]
    if not bad.empty:
        raise ValueError(f"X and Y must be numbers. Problem with: {list(bad[data_frame.columns[0]])}")

    cities = list(data_frame[data_frame.columns[0]])
    coordinates = {row[0]: (float(row[1]), float(row[2])) for row in data_frame.values}
    distances = {c: {} for c in cities}

    for index, city_1 in enumerate(cities):
        for city_2 in cities[index + 1:]:
            # Straight distance between the two points
            distance = ((coordinates[city_1][0] - coordinates[city_2][0])**2 + (coordinates[city_1][1] - coordinates[city_2][1])**2)**0.5
            distance = round(distance, decimals)
            # If the distance is a whole number, convert it to an integer
            if distance.is_integer():
                distance = int(distance)
            # Add the distance to the dictionary and mirror it for the symmetric property
            distances[city_1][city_2] = distance
            distances[city_2][city_1] = distance

    return coordinates, cities, distances

def held_karp(cities, distances, start=0):
    number_of_cities = len(cities)
    # Create a distance matrix for the cities based on the distances dictionary
    distance_matrix = [[0 if i == j else distances[cities[i]][cities[j]] for j in range(number_of_cities)] for i in range(number_of_cities)]
    
    INF = float('inf')
    number_of_subsets = range(2**number_of_cities)
    # create a 2D list to store the minimum cost to reach each city
    cost_matrix = [[INF] * number_of_cities for subset in number_of_subsets]
    # create a 2D list to store the parent city for each city
    parent_matrix = [[-1] * number_of_cities for subset in number_of_subsets]

    cost_matrix[1][0] = 0

    for subset in number_of_subsets:
        if not subset & (1 << start):
            continue
        for city_1 in range(number_of_cities):
            if not subset & (1 << city_1) or cost_matrix[subset][city_1] == INF:
                continue
            for city_2 in range(number_of_cities):
                if subset & (1 << city_2):
                    continue
                next_subset = subset | (2**city_2)
                cost = cost_matrix[subset][city_1] + distance_matrix[city_1][city_2]
                if cost < cost_matrix[next_subset][city_2]:
                    cost_matrix[next_subset][city_2] = cost
                    parent_matrix[next_subset][city_2] = city_1

    full = (1 << number_of_cities) - 1
    best, last = INF, -1
    for j in range(number_of_cities):
        if j != start and cost_matrix[full][j] + distance_matrix[j][start] < best:
            best, last = cost_matrix[full][j] + distance_matrix[j][start], j

    # reconstruct
    path, mask, j = [], full, last
    while j != -1:
        path.append(j)
        pj = parent_matrix[mask][j]
        mask ^= (1 << j)
        j = pj
    path.reverse()
    return best, [cities[i] for i in path] + [cities[start]]


def run_held_karp(cities, dist_matrix):
    """Run exact Held-Karp dynamic programming and return benchmark metrics."""
    import time
    t_start = time.perf_counter()
    distances = {
        c1: {c2: dist_matrix[i][j] for j, c2 in enumerate(cities) if i != j}
        for i, c1 in enumerate(cities)
    }
    cost, route_cities = held_karp(cities, distances, start=0)
    exec_time = time.perf_counter() - t_start
    city_to_idx = {city: idx for idx, city in enumerate(cities)}
    route_indices = [city_to_idx[c] for c in route_cities]
    return {
        "route": route_indices,
        "distance": cost,
        "time_sec": exec_time,
        "states": len(cities) * (1 << len(cities)),
    }


def main():
    filename = input("Enter the Excel filename : ")
    sheet_number = int(input("Enter the Excel sheet number (1 to 5) : ")) - 1
    file_path = project_root/"data"/filename
    if sheet_number < 0 or sheet_number > 4:
        raise ValueError(f'Invalid sheet number')
    coordinates, cities, distances = load_distances(file_path, sheet_number)

    cost, route = held_karp(cities, distances)
    print("Minimum distance:", cost)
    print(" -> ".join(route))


if __name__ == "__main__":
    main()
