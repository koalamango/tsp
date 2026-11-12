"""
Author: Oshanda Fernando
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]

PAD = 20 # empty space around the outermost points in pixels
WINDOW_PARAMETER = 20  # the window size in inches
PAUSE_TIME = 0.2  # time to pause between drawing lines in seconds

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

# load data from Excel file
sheet_number = int(input("Enter the Excel sheet number (1 to 5) : ")) - 1
file_path = project_root/"data"/"coordinates_5_cities.xlsx"
if sheet_number < 0 or sheet_number > 4:
    raise ValueError(f'Invalid sheet number')
coordinates, cities, distances = load_distances(file_path, sheet_number)

# global variables for the figure, canvas, and lines
figure = None
canvas = None
lines = []
dots = []

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

draw_map(WINDOW_PARAMETER, PAD)

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

# draw a dot at a city
def draw_dot(city):
    x, y = coordinates[city]
    dot, = canvas.plot([x], [y], marker="o", color="blue", markersize=12, zorder=2)
    dots.append(dot)
    figure.canvas.draw_idle()

# remove only the dots
def clear_dots():
    for dot in dots:
        dot.remove()
    dots.clear()
    figure.canvas.draw_idle()

# input: cities (list of city names), distances (dictionary of distances between cities)
# return: minimum distance and the ordered sequence of city names in the optimal route
def held_karp(cities, distances):
    number_of_cities = len(cities)
    
    # build a 2D distance matrix
    distance_matrix = [[0 if city_1 == city_2 else distances[cities[city_1]][cities[city_2]] for city_2 in range(number_of_cities)] for city_1 in range(number_of_cities)]
    
    INF = float('inf')
    number_of_subsets = 2 ** number_of_cities
    
    # 2D tables where rows represent different combinations and columns represent last visited cities
    cost_matrix = [[INF] * number_of_cities for subset in range(number_of_subsets)]
    # 2D table to track the parent city for each city in each subset
    parent_matrix = [[-1] * number_of_cities for subset in range(number_of_subsets)]

    # set the base case cost to 0 for starting at first location
    cost_matrix[1][0] = 0

    # consider all posible subset of given location list (Ex: binary subset value 1011 represent locations 3, 1, and 0)
    for subset in range(number_of_subsets):
        clear_lines()
        clear_dots()
        # check if the starting city is included in the subset (Ex: 1101 & 1 = True, 1100 & 1 = False)
        if subset & 1:
            # draw dots for all the cities in the subset
            [draw_dot(city) for index, city in enumerate(cities) if subset >> index & 1]
            for city_1 in range(number_of_cities):
                clear_lines()
                # check if the current city is included in the subset (Ex: 1101 & 100 = True, 1101 & 10 = False), and has a valid cost
                if (subset & (2 ** city_1)) and (cost_matrix[subset][city_1] != INF):
                    for city_2 in range(number_of_cities):
                        # check if the next city is not included in the subset (Ex: not(1101 & 10) = True, not(1101 & 100) = False)
                        if not (subset & (2 ** city_2)):
                            # calculate next subset (Ex: 1101 | 10 = 1111), and cost
                            next_subset = subset | (2 ** city_2)
                            cost = cost_matrix[subset][city_1] + distance_matrix[city_1][city_2]
                            # update cost if the new cost is lower than the previously recorded cost
                            draw_line(cities[city_1], cities[city_2])
                            if cost < cost_matrix[next_subset][city_2]:
                                cost_matrix[next_subset][city_2] = cost
                                parent_matrix[next_subset][city_2] = city_1

    # iterate through all ending cities, add their return cost to starting location
    last_subset = (2 ** number_of_cities) - 1
    minimum_distance, last_city = INF, -1
    
    for city in range(number_of_cities):
        if city != 0:
            return_cost = cost_matrix[last_subset][city] + distance_matrix[city][0]
            if return_cost < minimum_distance:
                minimum_distance, last_city = return_cost, city

    # backtrack through the parent matrix to get the complete tour
    route, subset, city = [], last_subset, last_city
    while city != -1:
        route.append(city)
        previous_city = parent_matrix[subset][city]
        # calculate previous subset by removing the current city from the subset (Ex: 1111 ^ 10 = 1101)
        subset = subset^(2 ** city)
        city = previous_city
        
    route.reverse()
    
    # Return the minimum total cost and the ordered sequence of city names
    return minimum_distance, [cities[i] for i in route] + [cities[0]]

cost, route = held_karp(cities, distances)
print("Minimum distance:", cost)
print(" -> ".join(route))

for i in range(len(route) - 1):
    draw_line(route[i], route[i + 1])

plt.ioff()
plt.show()
