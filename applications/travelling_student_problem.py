"""
Author: Oshanda Hembathanthrige
"""
import random
import math
from datetime import time as dtime
from openpyxl import load_workbook

#--------------------------------------------------------
# Load files
#--------------------------------------------------------

#EXCEL_FILE = input("Enter the path to the Excel file: ")
EXCEL_FILE = "timetable\\travelling_student_timetable.xlsx"
REQUIRED_SHEETS = ("Rooms", "Distances", "TimeSlots", "Courses", "Modules")

#===================================================
# Load data from the Excel file and validate it
#===================================================

# load data from the Excel file and return rooms, distances, time slots, courses, and modules as dictionaries/lists
def load_data(path):

    # clean up the data read from Excel, removing leading/trailing whitespace and converting to the appropriate type
    def clean(value):
        return value.strip() if isinstance(value, str) else value
    
    # yields rows of data from a worksheet, skipping the header row and any empty rows
    def data_rows(ws):
        rows = ws.iter_rows(values_only=True)
        next(rows, None)
        for row in rows:
            if row and row[0] is not None:
                yield row
    
    # raise an error if the data in the Excel file is inconsistent or incomplete
    def validate_data(rooms, distances, courses, modules):
    # check that all rooms in the distances sheet are present in the rooms dictionary
        for r1 in rooms:
            if r1 not in distances or any(r2 not in distances[r1] for r2 in rooms):
                raise ValueError(f"Distances sheet is missing entries for room {r1}")
        # check that all courses in the modules sheet are present in the courses dictionary
        for module_id, m in modules.items():
            unknown = [c for c in m["students"] if c not in courses]
            if unknown:
                raise ValueError(f"{module_id} refers to unknown course(s) {unknown}")
            needed = sum(courses[c] for c in m["students"])
            if not any(r["type"] == m["type"] and r["capacity"] >= needed for r in rooms.values()):
                raise ValueError(f"{module_id} needs a {m['type']} room for {needed} students, "f"but no such room exists. Check Rooms / Courses sheets.")
    
    wb = load_workbook(path, read_only=True, data_only=True)

    try:
        missing = [s for s in REQUIRED_SHEETS if s not in wb.sheetnames]
        if missing:
            raise ValueError(f"Missing sheet(s) in {path}: {missing}")
        
        # Rooms: Room | Type | Capacity
        rooms = {str(clean(r[0])): {"type": clean(r[1]).lower(),"capacity": int(r[2])}for r in data_rows(wb["Rooms"])}

        # Distances: square matrix, labels in first row and first column
        dist_rows = wb["Distances"].iter_rows(values_only=True)
        header = []
        for label in next(dist_rows)[1:]:
            if label is None:
                break
            header.append(str(clean(label)))
        distances = {}
        for r in dist_rows:
            if r and r[0] is not None:
                distances[str(clean(r[0]))] = {col: int(v) for col, v in zip(header, r[1:])}

        # TimeSlots: Slot | Time  (Excel may turn "09:00" into a time value)
        time_slots = [r[1].strftime("%H:%M") if isinstance(r[1], dtime) else str(clean(r[1])) for r in sorted(data_rows(wb["TimeSlots"]), key=lambda r: r[0])]

        # Courses: Course | Students
        courses = {str(clean(r[0])): int(r[1]) for r in data_rows(wb["Courses"])}

        # Modules: Module | Professor | Students | Type | Duration
        modules = {str(clean(r[0])): {"professor": str(clean(r[1])), "students": [c.strip() for c in str(r[2]).split(",") if c.strip()], "type": clean(r[3]).lower(), "duration": int(r[4])} for r in data_rows(wb["Modules"])}

    finally:
        wb.close()

    validate_data(rooms, distances, courses, modules)
    return rooms, distances, time_slots, courses, modules

#---------------------------------------------------------
# Load data
#---------------------------------------------------------

rooms, distances, time_slots, courses, modules = load_data(EXCEL_FILE)
times = [int(t.split(':')[0]) for t in time_slots]

#=================================================
# Find conflicting modules
#=================================================

# modules that cannot be sheduled at the same time
def generate_conflicts(modules):
    conflicts = {}
    for m1 in modules:
        conflicts[m1] = {}
        for m2 in modules:
            # compare all modules with each other
            if m1 != m2:
                # same professor cannot teach two modules at the same time
                same_professor = (modules[m1]["professor"] == modules[m2]["professor"])
                # same students cannot attend two modules at the same time
                common_students = (set(modules[m1]["students"]) & set(modules[m2]["students"]))
                # if either condition is true, the modules conflict
                conflicts[m1][m2] = (same_professor or len(common_students) > 0)
            else:
                conflicts[m1][m2] = False
    return conflicts

conflicts = generate_conflicts(modules)

# cheak if two modules overlap in the given order
def overlaps(start_1, duration_1, start_2, duration_2):
    end_1 = start_1 + duration_1
    end_2 = start_2 + duration_2
    return start_1 < end_2 and start_2 < end_1

# check if the given assignment is valid
def is_valid_assignment(module_id, start, room, timetable):

    module = modules[module_id]
    duration = module["duration"]

    # Check whether the module fits into the time slots
    if start not in times or (start + duration) not in times:
        return False

    # Check if the room type is right for the module
    if rooms[room]["type"] != module["type"]:
        return False

    # Check if the room capacity is enough
    if rooms[room]["capacity"] < sum([courses[course_id] for course_id in module["students"]]):
        return False

    # Compare with all previously assigned modules
    for other_id, other in timetable.items():
        other_start = other["time"]
        other_room = other["room"]
        other_duration = modules[other_id]["duration"]

        # Check whether their times overlap
        time_conflict = overlaps(start, duration, other_start, other_duration)

        if time_conflict:
            # Two modules cannot use the same room simultaneously
            if room == other_room:
                return False

            # Students or professors cannot attend two modules
            if conflicts[module_id][other_id]:
                return False
    return True

#================================================
# Timetable
#================================================

def generate_timetable():

    timetable = {}
    search_nodes = [0]
    max_nodes = 500000

    def backtrack():
        
        search_nodes[0] += 1
        # return false if serch node count excced max_nodes
        if search_nodes[0] > max_nodes:
            return False

        # return true if all modules have been assigned
        if len(timetable) == len(modules):
            return True

        selected_module = None
        selected_options = None
        selected_degree = -1

        # consider all modules one by one
        for module_id in modules:
            # proceed if current module_id is not in timetable
            if module_id not in timetable:
                options = []
                for start in times:
                    for room in rooms:
                        # check if valid assignments exsist for all posible module_ids, start times and rooms
                        if is_valid_assignment(module_id, start, room, timetable):
                            options.append((start, room))

                # return False if no valid options
                if len(options) == 0:
                    return False

                # number of modules that dosen't conflict with current module and are not in the timetable
                degree = sum(conflicts[module_id][other_id] for other_id in modules if other_id != module_id and other_id not in timetable)

                if (selected_options is None or len(options) < len(selected_options) or (len(options) == len(selected_options) and degree > selected_degree)):

                    selected_module = module_id
                    selected_options = options
                    selected_degree = degree

        # Try the available assignments in random order
        random.shuffle(selected_options)

        for start, room in selected_options:

            timetable[selected_module] = {"time": start, "room": room}

            if backtrack():
                return True

            del timetable[selected_module]

        return False

    if not backtrack():
        raise Exception("Could not generate a valid timetable.")

    # print("Initial timetable generated.")
    # print("Backtracking search nodes:", search_nodes[0])

    return timetable

#=====================================================
# Generate new timetables
#=====================================================

def generate_new_timetable(timetable, attempts=100):

    for attempt in range(attempts):

        new_timetable = {m: assignment.copy() for m, assignment in timetable.items()}
        # select one module randomly
        module_id = random.choice(list(modules.keys()))
        old_assignment = new_timetable.pop(module_id)

        possible_assignments = []

        for start in times:
            for room in rooms:
                # apply new times and rooms to find other valid assignments
                if (start != old_assignment["time"] or room != old_assignment["room"]):
                    if is_valid_assignment(module_id, start, room, new_timetable):
                        possible_assignments.append((start, room))

        if possible_assignments:
            new_start, new_room = random.choice(possible_assignments)
            new_timetable[module_id] = {"time": new_start, "room": new_room}
            return new_timetable

    return None

#================================================
# Travel distances
#================================================

def travel_distances(timetable):

    people = {}
    # sort journies by person
    for module_id, assignment in timetable.items():

        module = modules[module_id]
        professor = module["professor"]
        room = assignment["room"]
        start = assignment["time"]

        # add professor to the people list
        if professor not in people:
            people[professor] = []

        people[professor].append((start, room, module_id))

        for student in module["students"]:
            # add students to the people list
            if student not in people:
                people[student] = []

            people[student].append((start, room, module_id))

    individual_distances = {}
    total_distance = 0

    for person, classes in people.items():

        classes.sort(key=lambda x: x[0])
        personal_distance = 0

        # calculate distance travelled by each person to get the total distance
        for i in range(len(classes) - 1):

            previous_room = classes[i][1]
            next_room = classes[i + 1][1]

            distance = distances[previous_room][next_room]
            personal_distance += distance

        individual_distances[person] = personal_distance
        total_distance += personal_distance

    return total_distance, individual_distances

# ============================================================
# 8. SIMULATED ANNEALING
# ============================================================

def simulated_annealing(initial_timetable, iterations=50000, initial_temperature=1000, minimum_temperature=0.01):

    # initial variables
    current_timetable = {m: a.copy() for m, a in initial_timetable.items()}
    best_timetable = {m: a.copy() for m, a in initial_timetable.items()}
    current_distance, _ = travel_distances(current_timetable)
    best_distance = current_distance

    for iteration in range(iterations):

        # gradually reduce temperature
        progress = iteration / iterations
        temperature = initial_temperature * (minimum_temperature / initial_temperature) ** progress

        # generate a new timetable
        new_timetable = generate_new_timetable(current_timetable)

        if new_timetable:
            # difference between the two solutions
            new_distance, _ = travel_distances(new_timetable)
            difference = new_distance - current_distance

            # accept if new distance is smaller
            if difference < 0:
                accept = True

            else:
                probability = math.exp(-difference / temperature)
                accept = random.random() < probability

            if accept:
                current_timetable = new_timetable
                current_distance = new_distance

            # update if new distance is smaller than best solution
            if new_distance < best_distance:

                best_distance = new_distance
                best_timetable = {m: a.copy() for m, a in new_timetable.items()}

            # display progress
            # if (iteration + 1) % 10000 == 0:
            #     print("Iteration:", iteration + 1, "| Current distance:", current_distance, "| Best distance:", best_distance)

    return best_timetable, best_distance

# ============================================================
# Display results
# ============================================================

def display_timetable(timetable, out_file):
    sorted_modules = sorted(timetable.items(), key=lambda x: (x[1]["time"], x[0]))

    for module_id, assignment in sorted_modules:
        start = assignment["time"]
        room = assignment["room"]
        module = modules[module_id]

        print("-------------------------------------", file=out_file)
        print("Module:", module_id, file=out_file)
        print("Start time:", f"{start:02d}:00", file=out_file)
        print("Duration:", module["duration"], "hour(s)", file=out_file)
        print("Room:", room, file=out_file)
        print("Room type:", module["type"], file=out_file)
        print("Professor:", module["professor"], file=out_file)
        print("Students:", module["students"], file=out_file)

    print("-------------------------------------", file=out_file)

def display_distances(timetable, out_file):
    total, individual = travel_distances(timetable)

    print("\n---------- INDIVIDUAL DISTANCES ----------\n", file=out_file)
    for person, distance in sorted(individual.items()):
        print(person, ":", distance, "metres", file=out_file)

    print("\n-----------------------------------------", file=out_file)
    print("TOTAL TRAVEL DISTANCE:", total, "metres", file=out_file)
    print("------------------------------------------", file=out_file)

# ============================================================
# Main program
# ============================================================

random.seed(42)

# generate initial valid timetable
initial_timetable = generate_timetable()
initial_distance, _ = travel_distances(initial_timetable)

# optimise timetable using simulated annealing
best_timetable, best_distance = simulated_annealing(initial_timetable)

# open text file and save results inside it
with open("results/timetable_results.txt", "w") as f:
    print("\nInitial distance:", initial_distance, "metres", file=f)
    print("Optimised distance:", best_distance, "metres", file=f)
    # check for zero devision error and unrialistic values
    if initial_distance > 0:
        improvement = ((initial_distance - best_distance) / initial_distance) * 100
        print("Distance reduction:", round(improvement, 2), "%", file=f)

    print("\n\n========== INITIAL RESULTS ==========", file=f)
    display_timetable(initial_timetable, out_file=f)
    display_distances(initial_timetable, out_file=f)

    print("\n\n========== OPTIMISATION RESULTS ==========", file=f)
    display_timetable(best_timetable, out_file=f)
    display_distances(best_timetable, out_file=f)

print("=================================================")
print("Results saved to : results/timetable_results.txt ")
print("=================================================")
