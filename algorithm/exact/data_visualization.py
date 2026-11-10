"""
Author: Oshanda Hembathanthrige

Allows for visualisation of the brute force and branch and bound algorithms
"""

# run this in terminal to install the required packages: py -m pip install pandas openpyxl
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PAD = 20 # empty space around the outermost points in pixels
WINDOW_PARAMETER = 20  # the window size in inches
PAUSE_TIME = 0.1  # time to pause between drawing lines in seconds

# Read an Excel sheet with columns (Location, X, Y). Returns (coordinates, cities, distances), decimals=0 for easy computation.
def load_distances(path, sheet_name=0, decimals=0):
    resolved_path = Path(path)
    if not resolved_path.exists():
        for candidate in (PROJECT_ROOT / path, PROJECT_ROOT / "data" / path):
            if candidate.exists():
                resolved_path = candidate
                break
    try:
        data_frame = pd.read_excel(resolved_path, sheet_name=sheet_name)
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

# Load the locations and the distance matrix
filename = input("Enter the Excel filename: ")
coordinates, cities, distances = load_distances(filename)

# global variables for the figure, canvas, and lines
figure = None
canvas = None
lines = []

# create the window and draw every location as a dot with its name
def draw_map(WINDOW_PARAMETER, PAD):
    global figure, canvas
    plt.ion()
    # extract the x and y coordinates from the dictionary
    xs = [x for x, y in coordinates.values()]
    ys = [y for x, y in coordinates.values()]
    # figure out the width and height of the window
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) + 2 * PAD
    height = (max_y - min_y) + 2 * PAD
    scale = WINDOW_PARAMETER/(width+height)
    figure, canvas = plt.subplots(figsize=(width * scale, height * scale))

    # set the view limits and aspect ratio of the x,y axes
    canvas.set_xlim(min_x - PAD, max_x + PAD)
    canvas.set_ylim(min_y - PAD, max_y + PAD)
    canvas.set_aspect("equal")

    for name, (x, y) in coordinates.items():
        canvas.plot(x, y, "o", color="black", zorder=3)
        canvas.annotate(name, (x, y), xytext=(6, 0), textcoords="offset points", va="center", zorder=3)

    plt.show()
    plt.pause(PAUSE_TIME)


# draw a line between two cities
def draw_line(city_1, city_2):
    (x1, y1), (x2, y2) = coordinates[city_1], coordinates[city_2]
    line, = canvas.plot([x1, x2], [y1, y2], color="red", linewidth=2, zorder=1)
    lines.append(line)
    figure.canvas.draw_idle()
    plt.pause(PAUSE_TIME)


# remove only the lines
def clear_lines():
    for line in lines:
        line.remove()
    lines.clear()
    figure.canvas.draw_idle()
    plt.pause(PAUSE_TIME)


draw_map(WINDOW_PARAMETER, PAD)

draw_line("London","Bristol")

plt.ioff()
plt.show()