# run this in terminal to install the required packages: py -m pip install pandas openpyxl
import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]

# Read an Excel sheet with columns (Location, X, Y). Returns (coordinates, cities, distances), decimals=0 for easy computation
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

filename = input("Enter the Excel filename : ")
sheet_number = int(input("Enter the Excel sheet number (1 to 5) : ")) - 1
file_path = project_root/"data"/filename
if sheet_number < 0 or sheet_number > 4:
    raise ValueError(f'Invalid sheet number')

coordinates, cities, distances = load_distances(file_path, sheet_number)

print("\nCoordinates:")
print(coordinates)
print("\nCities:")
print(cities)
print("\nDistances")
print(distances)
print()