"""
Author: Oshanda Fernando
"""

# run this in terminal to install the required packages: py -m pip install pandas openpyxl
import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]

#Read an Excel sheet (only one triangle needed), Returns (cities, distances)
def load_distance(path, sheet_name=0):
    data_frame = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
    # Remove empty spaces from column and row names (Ex: " Canary wharf " -> "Canary wharf")
    data_frame.columns = [str(c).strip() for c in data_frame.columns]
    data_frame.index = [str(i).strip() for i in data_frame.index]
    # Check if row and column city names match and are in same order
    if set(data_frame.columns) != set(data_frame.index):
        raise ValueError("Row and column city names don't match")

    cities = list(data_frame.columns)
    distances = {c: {} for c in cities}

    for a in cities:
        for b in cities:
            value = data_frame.loc[a, b]
            # Continue to next city if two cities match or the cell is empty
            if a == b or pd.isna(value):
                continue
            # Convert the value to a float or int
            distance = value.item()
            # If the distance is a whole number, convert it to an integer (for faster processing)
            if distance.is_integer():
                distance = int(distance)
            # Check for conflicts if the distance already exists in the dictionary
            if b in distances[a] and distances[a][b] != distance:
                raise ValueError(f"Conflict for {a}-{b}: {distances[a][b]} vs {distance}")
            # Add the distance to the dictionary and mirror it for the symmetric property
            distances[a][b] = distance
            distances[b][a] = distance

    return cities, distances

filename = input("Enter the Excel filename : ")
file_path = project_root/"data"/filename

cities, distances = load_distance(file_path)

print()
print("Cities:")
print(cities)
print()
print("Distances:")
print(distances)
print()
