"""
Author: Oshanda Hembathanthrige
"""
# run this in terminal to install the required packages: py -m pip install pandas openpyxl
import pandas as pd

#Read an Excel sheet (only one triangle needed), Returns (cities, distances).
def load_distance(path, sheet_name=0):
    df = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
    # Remove empty spaces from column and row names (Ex: " Canary wharf " -> "Canary wharf")
    df.columns = [str(c).strip() for c in df.columns]
    df.index = [str(i).strip() for i in df.index]
    # Check if row and column city names match and are in same order
    if set(df.columns) != set(df.index):
        raise ValueError("Row and column city names don't match")

    cities = list(df.columns)
    distances = {c: {} for c in cities}

    for a in cities:
        for b in cities:
            value = df.loc[a, b]
            # Continue to next city if two cities match or the cell is empty
            if a == b or pd.isna(value):
                continue
            # Convert the value to a float or int
            d = value.item()
            # If the distance is a whole number, convert it to an integer (for faster processing)
            if d.is_integer():
                d = int(d)
            # Check for conflicts if the distance already exists in the dictionary
            if b in distances[a] and distances[a][b] != d:
                raise ValueError(f"Conflict for {a}-{b}: {distances[a][b]} vs {d}")
            # Add the distance to the dictionary and mirror it for the symmetric property
            distances[a][b] = d
            distances[b][a] = d

    return cities, distances

filename = input("Enter the Excel filename: ")
cities, distances = load_distance(filename)
print(cities)
print(distances)