"""
Author: Oshanda Fernando
"""

import itertools
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


def main():
    # Load the locations and the distance matrix
    filename = input("Enter the Excel filename (ex: coordinates_10_cities.xlsx) : ")
    sheet_number = int(input("Enter the Excel sheet number (1 to 5) : ")) - 1
    file_path = project_root/"data"/filename
    if sheet_number < 0 or sheet_number > 4:
        raise ValueError(f'Invalid sheet number')

    coordinates, cities, distances = load_distances(file_path, sheet_number)

    # Lock the starting location and find the remaining targets
    start_city = 'London'
    other_cities = [c for c in cities if c != start_city]

    best_route = None
    min_distance = float('inf')

    # Use brute force to check every possible permutation of the route
    for perm in itertools.permutations(other_cities):
        # Construct a complete round-trip loop
        current_route = [start_city] + list(perm) + [start_city]
        current_distance = 0
        # Accumulate the leg distances for the path
        for i in range(len(current_route) - 1):
            from_city = current_route[i]
            to_city = current_route[i+1]
            current_distance += distances[from_city][to_city]
            
        # Track the absolute shortest loop found so far
        if current_distance < min_distance:
            min_distance = current_distance
            best_route = current_route

    #Draw the best route
    for i in range(len(best_route) - 1):
        from_city = best_route[i]
        to_city = best_route[i+1]

    # Output the results
    print(f"Optimal Route: {' -> '.join(best_route)}")
    print(f"Minimum Distance: {min_distance} miles")


if __name__ == "__main__":
    main()
