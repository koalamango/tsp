# Travelling Salesperson Problem (TSP) Algorithms

A Python repository implementing, analyzing, and benchmarking classical and modern algorithms for the **Travelling Salesperson Problem (TSP)**.

The project provides implementations ranging from exact solvers (brute-force permutation search with real-time visualization, and Mixed-Integer Linear Programming via HiGHS) to greedy constructive heuristics, local-search tour improvements (2-Opt, 3-Opt), and stochastic metaheuristics (Simulated Annealing and Ant Colony Optimization).

---

## Contributors
- **Richard Clark** 
- **Oshanda Hembathanthrige** 
- **Tyrone Sequeira**
- **Jessie W**

## Table of Contents

- [Overview](#overview)
- [Implemented Algorithms](#implemented-algorithms)
  - [Exact Methods](#1-exact-methods)
  - [Constructive Heuristics](#2-constructive-heuristics)
  - [Local Search & Improvement Heuristics](#3-local-search--improvement-heuristics)
  - [Metaheuristics](#4-metaheuristics)
- [Algorithm Complexity & Comparison](#algorithm-complexity--comparison)
- [Repository Structure](#repository-structure)
- [Data Formats](#data-formats)
- [Installation & Requirements](#installation--requirements)
- [Usage](#usage)
  - [Unified Algorithm Orchestrator](#unified-algorithm-orchestrator-tsp_loaderpy)
  - [Nearest Neighbour](#running-nearest-neighbour)
  - [2-Opt Refinement](#running-2-opt)
  - [3-Opt Refinement](#running-3-opt)
  - [Branch and Bound](#running-branch-and-bound)
  - [Brute Force with Real-Time Visualization](#running-brute-force-visualizer)
  - [Metaheuristics (Simulated Annealing & ACO)](#running-metaheuristics)
  - [Data Loading Utilities](#data-loading-utilities)
- [Output Reports](#output-reports)

---

## Overview

Given a list of cities and the distances between each pair, the Travelling Salesperson Problem asks: *What is the shortest possible route that visits each city exactly once and returns to the origin city?*

Because TSP is NP-hard, exact approaches become intractable as the number of cities $n$ grows. This repository demonstrates how different algorithmic paradigms balance computational complexity, execution time, and solution quality:

1. **Exact Solvers** guarantee the global optimum for small problem instances or benchmark baselines.
2. **Heuristics** rapidly generate good solutions (e.g., within milliseconds for $n = 20$).
3. **Local Search** iteratively eliminates route crossings and suboptimal connections.
4. **Metaheuristics** escape local optima to discover near-optimal solutions on larger graphs.

---

## Implemented Algorithms

### 1. Exact Methods

- **Brute-Force Search with Live Visualization (`brute_force_visualized.py`)**:
  - Evaluates all $(n - 1)!$ permutations starting and ending at a fixed city (e.g., London).
  - Features real-time animated plotting in Matplotlib, displaying current route evaluations, best-so-far distances, and the final optimal tour, as well as a headless runner (`run_brute_force`) used by `tsp_loader.py`.
  - Benchmarks recorded in `Brute Force - Results.txt` illustrate the factorial explosion ($n = 12$ requires checking 39.9M routes in ~110 seconds without pruning, or ~2.17 seconds with branch-and-bound pruning).

- **Branch and Bound (`branch_and_bound.py`)**:
  - Exact depth-first tree search with admissible lower-bound pruning based on each unvisited city's minimum outgoing edge.
  - Uses an initial heuristic upper bound (e.g. Nearest Neighbour or 2-Opt) to prune suboptimal partial tours early, dramatically reducing the search space compared to exhaustive brute force.

- **HiGHS Mixed-Integer Linear Programming (`scipy.optimize.milp`)**:
  - Embedded in `nearest_neighbour.py` and `three_opt.py` as an exact ground-truth solver.
  - Employs the Dantzig-Fulkerson-Johnson (DFJ) formulation with dynamic subtour-elimination cuts.
  - Proves the true global optimum ($\text{MIP gap} = 0.0$) to benchmark heuristic accuracy.

### 2. Constructive Heuristics

- **Nearest Neighbour (`nearest_neighbour.py`)**:
  - Greedily extends the tour by choosing the closest unvisited city at each step until a full cycle is formed.
  - Runs in $O(n^2)$ time with exactly $n(n - 1) / 2$ candidate-distance examinations.
  - Automatically compares against the exact MILP solution and outputs an audit report (`outputs/<input>_nearest_neighbour_results.md`).

### 3. Local Search & Improvement Heuristics

- **2-Opt Local Search (`two_opt.py`)**:
  - Takes an initial tour (constructed via Nearest Neighbour) and iteratively eliminates crossed edges by reversing tour segments.
  - Implements best-improvement 2-opt: evaluates all non-adjacent edge pairs ($n(n - 3) / 2$ pairs per complete scan) in $O(1)$ difference calculation per pair.
  - Reconstructs only accepted moves in $O(n)$, repeating scans until a local optimum is reached ($O(p \cdot n^2)$ where $p$ is the number of passes).

- **3-Opt Local Search (`three_opt.py`)**:
  - Evaluates all $\binom{n}{3} = n(n - 1)(n - 2) / 6$ edge triplets and tests all 7 valid reconnection arrangements per triplet.
  - Tests each candidate reconnection in $O(1)$ arithmetic without copying full arrays; rebuilds only accepted moves in $O(n)$.
  - Provides deeper optimization than 2-opt, escaping 2-optimal local minima.

### 4. Metaheuristics

- **Simulated Annealing (`metaheuristic.py`)**:
  - Probabilistic technique based on thermal annealing.
  - Uses geometric cooling ($T_{k+1} = \alpha \cdot T_k$) and the Metropolis acceptance criterion ($\Delta < 0$ or $P < e^{-\Delta / T}$).
  - Employs a hybrid neighborhood operator: 70% 2-opt segment reversals and 30% 2-city swaps.

- **Ant Colony Optimization (ACO) (`metaheuristic.py`)**:
  - Nature-inspired population metaheuristic (Ant System).
  - Uses pheromone trails ($\tau_{ij}$) and distance visibility ($\eta_{ij} = 1 / d_{ij}$).
  - Artificial ants construct tours stochastically based on transition probabilities $P_{ij} \propto (\tau_{ij})^\alpha \cdot (\eta_{ij})^\beta$, followed by pheromone evaporation and deposit reinforcement.

---

## Algorithm Complexity & Comparison

| Algorithm | Paradigm | Time Complexity | Optimality Guarantee | Scalability |
|:---|:---|:---:|:---:|:---|
| **Brute Force** | Exact / Exhaustive | $O((n - 1)!)$ | Global optimum guaranteed | Small instances only ($n \le 12$) |
| **Branch and Bound** | Exact / Pruned | Exponential (worst case) | Global optimum guaranteed | Moderate instances |
| **HiGHS MILP (DFJ cuts)** | Exact / Mathematical Programming | Exponential (worst case) | Global optimum within tolerance | Fast on moderate instances ($n \le 50$) |
| **Nearest Neighbour (NN)** | Greedy Constructive | $O(n^2)$ | None (local greedy choices) | Very fast ($n > 10,000$) |
| **2-Opt (from NN)** | Local Search | $O(p \cdot n^2)$ | 2-optimal (local minimum) | Fast ($n \le 1,000$) |
| **3-Opt (from NN)** | Local Search | $O(p \cdot n^3)$ | 3-optimal (local minimum) | Moderate ($n \le 200$) |
| **Simulated Annealing** | Metaheuristic | $O(k \cdot n)$ | Near-optimal (asymptotically optimal) | Scales to large $n$ |
| **Ant Colony Optimization** | Metaheuristic | $O(I \cdot m \cdot n^2)$ | Near-optimal heuristic | Scales to large $n$ |

*Notes: $n$ = number of cities; $p$ = number of scan passes until convergence; $k$ = annealing iterations; $I$ = ACO iterations; $m$ = number of ants.*

---

## Repository Structure

```text
tsp_algorithms/
├── tsp_loader.py                   # Unified orchestrator to run all algorithms & generate comparison tables
├── brute_force_visualized.py       # Exhaustive search with animated Matplotlib circular visualization
├── branch_and_bound.py             # Exact branch-and-bound solver with partial-tour pruning
├── nearest_neighbour.py            # Nearest neighbour heuristic + HiGHS exact solver & report generator
├── two_opt.py                      # 2-opt local search refinement with detailed performance metrics
├── three_opt.py                    # 3-opt local search (7 reconnection cases) with performance report
├── metaheuristic.py                # Simulated Annealing and Ant Colony Optimization implementations
├── xlsx_dictionary.py              # Data loader for symmetric Excel distance matrices
├── xlsx_cartesian_dictionary.py    # Data loader for 2D Cartesian coordinate Excel sheets
├── requirements.txt                # Project package dependencies
│
├── Brute Force - Results.txt       # Benchmarking log for brute-force & branch-and-bound runs
│
└── data/
    ├── cities_10_cartesian.xlsx    # 10-city dataset (City, X, Y coordinates)
    ├── cities_20_cartesian.xlsx    # 20-city dataset (City, X, Y coordinates)
    ├── cities_40_cartestian.xlsx   # 40-city dataset (City, X, Y coordinates)
    └── distances_20_cities.xlsx    # 20-city symmetric distance matrix
```

---

## Data Formats

The project supports two Excel data formats:

### 1. Cartesian Coordinates (`cities_*.xlsx`)
Spreadsheets with columns: `City` (or `Location`), `X`, `Y`.
- The first city listed is treated as the starting/finishing depot.
- Straight-line Euclidean distance $d = \sqrt{(x_1 - x_2)^2 + (y_1 - y_2)^2}$ is used.

### 2. Distance Matrix (`distances_*.xlsx`)
Spreadsheets where rows and columns contain identical city names, and cell values represent symmetric pair-wise distances. Both upper and lower triangles are supported.

---

## Installation & Requirements

The project requires **Python 3.10+**.

### 1. Set up a Virtual Environment (Recommended)

On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

Install all required packages using [`requirements.txt`](file:///C:/Users/philr/PycharmProjects/tsp_algorithms/requirements.txt):

```bash
pip install -r requirements.txt
```

The dependencies include:
- `pandas`: Tabular data loading and manipulation for Excel distance matrices and coordinate sheets.
- `openpyxl`: Excel `.xlsx` reader engine used by pandas and the standalone loaders.
- `scipy`: Mixed-Integer Linear Programming solver (`scipy.optimize.milp` / HiGHS) for finding provable ground-truth optimal routes with subtour-elimination cuts.
- `numpy`: Matrix and vector operations for MILP constraint matrices, distance lookups, and metaheuristic operators.
- `matplotlib`: Dynamic visualization and route animations for the brute-force visualizer.

---

## Usage

### Unified Algorithm Orchestrator (`tsp_loader.py`)

Run all algorithms in turn across the 10-city, 20-city, and 40-city Cartesian datasets, automatically generating comparative benchmark tables:

```bash
# Run the complete suite on 10, 20, and 40-city datasets (includes 10-city brute-force & branch-and-bound demo)
python tsp_loader.py

# Specify custom Cartesian dataset paths
python tsp_loader.py -s data/cities_10_cartesian.xlsx -c data/cities_20_cartesian.xlsx -l data/cities_40_cartestian.xlsx

# Skip exact MILP solver baseline
python tsp_loader.py --no-exact
```

---

### Running Individual Algorithms

#### Running Nearest Neighbour
Constructs a greedy tour, calculates the exact MILP optimum, and produces a Markdown report:

```bash
python nearest_neighbour.py data/cities_20_cartesian.xlsx
```
*(Or run `python nearest_neighbour.py` and enter the file path interactively.)*

### Running 2-Opt
Generates a Nearest Neighbour tour and iteratively applies 2-opt edge-reversal moves:

```bash
python two_opt.py data/cities_20_cartesian.xlsx
```

### Running 3-Opt
Generates a Nearest Neighbour tour and applies 3-opt triplet reconnections:

```bash
python three_opt.py data/cities_20_cartesian.xlsx
```

### Running Branch and Bound
Solves a Cartesian dataset to global optimality using Branch and Bound seeded with a Nearest Neighbour upper bound:

```bash
python branch_and_bound.py data/cities_10_cartesian.xlsx
```

### Running Brute Force Visualizer
Launches an animated circular graph displaying tour permutations in real time:

```bash
python brute_force_visualized.py
```
*Prompt: Enter the filename (e.g., `data/distances_20_cities.xlsx`).*

### Running Metaheuristics
Import and run Simulated Annealing or Ant Colony Optimization in a script or interactive session:

```python
from metaheuristic import load_distance_excel, solve_tsp_sa, solve_tsp_aco

cities, dist_matrix = load_distance_excel("data/distances_20_cities.xlsx")

# Solve via Simulated Annealing
sa_result = solve_tsp_sa(dist_matrix, t_init=500.0, alpha=0.997, max_iter=8000, seed=42)
print("SA Best Distance:", sa_result["distance"])

# Solve via Ant Colony Optimization
aco_result = solve_tsp_aco(dist_matrix, n_ants=20, n_iter=150, seed=42)
print("ACO Best Distance:", aco_result["distance"])
```

### Data Loading Utilities
Inspect parsed coordinates or distance matrices:

```bash
python xlsx_cartesian_dictionary.py
python xlsx_dictionary.py
```

---

## Output Reports

All execution scripts (`nearest_neighbour.py`, `two_opt.py`, `three_opt.py`, `branch_and_bound.py`, and `tsp_loader.py`) automatically save formatted Markdown (`.md`) reports into the dedicated [`outputs/`](file:///C:/Users/philr/PycharmProjects/tsp_algorithms/outputs) directory (e.g. `outputs/cities_20_cartesian_two_opt_results.md`).

Each individual algorithm report includes:
- **Route Quality**: Final distance, theoretical shortest distance (via HiGHS MILP), percentage of optimum, and distance excess.
- **Efficiency Metrics**: Execution times, candidate examination counts, complete pass counts ($p$), and accepted moves.
- **Complexity Analysis**: Theoretical operation-count formulas and Big-O notation.
- **Complete Tour Itineraries**: Numbered, step-by-step city visiting orders for both the heuristic route and the proven optimal tour.

The orchestrator (`tsp_loader.py`) also writes side-by-side comparison tables across all algorithms into `outputs/tsp_loader_<dataset>_results.md`.