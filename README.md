# Travelling Salesperson Problem (TSP) Algorithms

A Python repository implementing, analyzing, and benchmarking classical and modern algorithms for the **Travelling Salesperson Problem (TSP)**.

The project provides implementations ranging from exact solvers (brute-force permutation search with real-time visualization, and Mixed-Integer Linear Programming via HiGHS) to greedy constructive heuristics, local-search tour improvements (2-Opt, 3-Opt), and stochastic metaheuristics (Simulated Annealing and Ant Colony Optimization).

---

## Contributors
- **Richard Clark** (Heuristics)
- **Oshanda Hembathanthrige** (Exact Methods)
- **Tyrone Sequeira** (Approximation)
- **Jessie W** (Metaheuristics)

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
  - [Unified Algorithm Orchestrator (`tsp_loader.py`)](#unified-algorithm-orchestrator-tsp_loaderpy)
  - [Running Individual Solvers](#running-individual-solvers)
  - [Interactive Visualizers](#interactive-visualizers)
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

- **Brute-Force Search with Live Visualization (`algorithm/exact/brute_force_visualized.py`)**:
  - Evaluates all $(n - 1)!$ permutations starting and ending at a fixed city (e.g., London).
  - Features real-time animated plotting in Matplotlib, displaying current route evaluations, best-so-far distances, and the final optimal tour, as well as a headless runner (`run_brute_force`) used by `tsp_loader.py`.
  - Demonstrates the factorial explosion of exhaustive search ($n = 12$ requires checking 39.9M routes in ~110 seconds without pruning, or ~2.17 seconds with branch-and-bound pruning).

- **Branch and Bound (`algorithm/exact/branch_and_bound.py`)**:
  - Exact depth-first tree search with admissible lower-bound pruning based on each unvisited city's minimum outgoing edge.
  - Uses an initial heuristic upper bound (e.g. Nearest Neighbour or 2-Opt) to prune suboptimal partial tours early, dramatically reducing the search space compared to exhaustive brute force.

- **HiGHS Mixed-Integer Linear Programming (`scipy.optimize.milp`)**:
  - Embedded in `algorithm/heuristics/nearest_neighbour.py` and `algorithm/heuristics/three_opt.py` as an exact ground-truth solver.
  - Employs the Dantzig-Fulkerson-Johnson (DFJ) formulation with dynamic subtour-elimination cuts.
  - Proves the true global optimum ($\text{MIP gap} = 0.0$) to benchmark heuristic accuracy.

### 2. Constructive Heuristics

- **Nearest Neighbour (`algorithm/heuristics/nearest_neighbour.py`)**:
  - Greedily extends the tour by choosing the closest unvisited city at each step until a full cycle is formed.
  - Runs in $O(n^2)$ time with exactly $n(n - 1) / 2$ candidate-distance examinations.
  - Automatically compares against the exact MILP solution and outputs an audit report (`outputs/<input>_nearest_neighbour_results.md`).
  - Includes an interactive step-by-step visualizer (`algorithm/heuristics/nearest_neighbour_visualization.py`).

### 3. Local Search & Improvement Heuristics

- **2-Opt Local Search (`algorithm/heuristics/two_opt.py`)**:
  - Takes an initial tour (constructed via Nearest Neighbour) and iteratively eliminates crossed edges by reversing tour segments.
  - Implements best-improvement 2-opt: evaluates all non-adjacent edge pairs ($n(n - 3) / 2$ pairs per complete scan) in $O(1)$ difference calculation per pair.
  - Reconstructs only accepted moves in $O(n)$, repeating scans until a local optimum is reached ($O(p \cdot n^2)$ where $p$ is the number of passes).
  - Includes an interactive edge-swap visualizer (`algorithm/heuristics/two_opt_visualization.py`).

- **3-Opt Local Search (`algorithm/heuristics/three_opt.py`)**:
  - Evaluates all $\binom{n}{3} = n(n - 1)(n - 2) / 6$ edge triplets and tests all 7 valid reconnection arrangements per triplet.
  - Tests each candidate reconnection in $O(1)$ arithmetic without copying full arrays; rebuilds only accepted moves in $O(n)$.
  - Provides deeper optimization than 2-opt, escaping 2-optimal local minima.
  - Includes an interactive triplet-reconnection visualizer (`algorithm/heuristics/three_opt_visualization.py`).

### 4. Metaheuristics

- **Simulated Annealing (`algorithm/metaheuristics/metaheuristic.py` & `algorithm/metaheuristics/simulated_annealing_visualized.py`)**:
  - Probabilistic technique based on thermal annealing.
  - Uses geometric cooling ($T_{k+1} = \alpha \cdot T_k$) and the Metropolis acceptance criterion ($\Delta < 0$ or $P < e^{-\Delta / T}$).
  - Employs a hybrid neighborhood operator: 70% 2-opt segment reversals and 30% 2-city swaps.
  - Includes an animated multi-panel visualizer (`algorithm/metaheuristics/simulated_annealing_visualized.py`) with live route evolution, distance convergence, and cooling curves.

- **Ant Colony Optimization (ACO) (`algorithm/metaheuristics/metaheuristic.py`)**:
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

*Notes: $n$ = number of cities; $p$ = number of scan passes until convergence; $k$ = annealing iterations (`tsp_loader.py` uses $k = \max(8000,\ 50n^2)$); $I$ = ACO iterations; $m$ = number of ants.*

---

## Repository Structure

```text
tsp/
├── tsp_loader.py                                   # Unified orchestrator to run all algorithms & generate comparison tables
├── requirements.txt                                # Project package dependencies
├── README.md                                       # Project documentation
│
├── algorithm/
│   ├── exact/
│   │   ├── brute_force_visualized.py               # Exhaustive search with animated Matplotlib circular visualization
│   │   ├── branch_and_bound.py                     # Exact branch-and-bound solver with partial-tour pruning
│   │   └── data_visualization.py                   # 2D coordinate map plotter for city datasets
│   │
│   ├── approximation/                              # Approximation algorithms directory
│   │   └── christofides.py                         # Christofides approximation algorithm
│   │
│   ├── heuristics/
│   │   ├── nearest_neighbour.py                    # Nearest neighbour heuristic + HiGHS exact solver & report generator
│   │   ├── nearest_neighbour_visualization.py      # Interactive click-through Nearest Neighbour visualizer
│   │   ├── two_opt.py                              # 2-opt local search refinement with detailed performance metrics
│   │   ├── two_opt_visualization.py                # Interactive click-through 2-opt move visualizer
│   │   ├── three_opt.py                            # 3-opt local search (7 reconnection cases) with performance report
│   │   ├── three_opt_visualization.py              # Interactive click-through 3-opt move visualizer
│   │   └── visualization_window.py                 # Screen-fitting and click-event helpers for Matplotlib windows
│   │
│   └── metaheuristics/
│       ├── metaheuristic.py                        # Simulated Annealing and Ant Colony Optimization implementations
│       └── simulated_annealing_visualized.py       # Animated Simulated Annealing visualizer with live convergence & GIF export
│
├── utils/
│   ├── tsp_charts.py                               # Matplotlib chart generator for per-dataset and scalability reports
│   ├── tsp_data.py                                 # Unified dataset loader (Cartesian coordinates & symmetric distance matrices)
│   ├── tsp_utils.py                                # Shared gap-formatting, tour list, and Markdown table helpers
│   ├── xlsx_dictionary.py                          # Standalone data loader for symmetric Excel distance matrices
│   └── xlsx_cartesian_dictionary.py                # Standalone data loader for 2D Cartesian coordinate Excel sheets
│
├── outputs/                                        # Generated Markdown reports and per-run CSV exports (created on first run)
│   └── charts/                                     # Generated PNG charts and GIF animations
│
└── data/
    ├── cities_10_bad_two_opt.xlsx                  # 10-city dataset illustrating 2-opt local optima
    ├── cities_10_clustered_bad_nn.xlsx             # 10-city clustered dataset illustrating greedy NN pitfalls
    ├── coordinates_5_cities.xlsx                   # 5-city coordinate dataset (City, X, Y coordinates)
    ├── coordinates_10_cities.xlsx                  # 10-city coordinate dataset (City, X, Y coordinates)
    ├── coordinates_20_cities.xlsx                  # 20-city coordinate dataset (City, X, Y coordinates)
    ├── coordinates_40_cities.xlsx                  # 40-city coordinate dataset (City, X, Y coordinates)
    ├── coordinates_80_cities.xlsx                  # 80-city coordinate dataset (City, X, Y coordinates)
    └── distances_20_cities.xlsx                    # 20-city symmetric distance matrix
```

---

## Data Formats

The project supports two Excel data formats:

### 1. Cartesian Coordinates (`coordinates_*.xlsx`)
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

Install all required packages using [`requirements.txt`](requirements.txt):

```bash
pip install -r requirements.txt
```

The project relies on standard scientific Python packages (`scipy`, `numpy`, `pandas`, `matplotlib`, `openpyxl`).

---

## Usage

### Unified Algorithm Orchestrator (`tsp_loader.py`)

Run all algorithms across benchmark datasets, automatically generating comparative benchmark tables, per-dataset runtime/distance charts, and cross-dataset scalability summaries. `tsp_loader.py` auto-detects both **Cartesian coordinate** spreadsheets and **symmetric distance matrix** sheets. Each algorithm is run several times per dataset (10 by default) so that runtime, and for stochastic algorithms solution quality, can be reported as min / mean / max / standard deviation:

```bash
# Run the complete default benchmark suite (10, 20, 40, and 80-city Cartesian datasets)
python tsp_loader.py

# Run on specific Cartesian coordinate datasets:
python tsp_loader.py data/coordinates_10_cities.xlsx
python tsp_loader.py data/coordinates_5_cities.xlsx data/coordinates_10_cities.xlsx data/coordinates_20_cities.xlsx

# Run on symmetric distance matrix datasets:
python tsp_loader.py data/distances_20_cities.xlsx

# Change the number of runs per algorithm (default 10, must be at least 1)
python tsp_loader.py --runs 25

# Change the base seed for Simulated Annealing / Ant Colony (default 42; run i uses seed + i)
python tsp_loader.py --seed 7

# Skip exact MILP solver baseline (gap vs optimum and optimum hit rate become N/A)
python tsp_loader.py --no-exact
```

| Option | Description | Default |
|:---|:---|:---|
| `datasets` | Optional dataset filepaths (Cartesian coordinates or symmetric distance matrices, e.g. `data/coordinates_10_cities.xlsx` or `data/distances_20_cities.xlsx`). If omitted, runs default suite | `CARTESIAN_SUITES` |
| `--runs`, `-r` | Number of timed runs per algorithm | `10` |
| `--seed` | Base random seed for Simulated Annealing and Ant Colony (run *i* uses `seed + i`) | `42` |
| `--no-exact` | Skip the exact MILP baseline | off |

See [Output Reports](#output-reports) for what is measured and recorded.

---

### Running Individual Solvers

Each algorithm can also be executed standalone on any Cartesian coordinate (`coordinates_*.xlsx`) or distance matrix (`distances_*.xlsx`) dataset:

```bash
# Nearest Neighbour (constructs greedy tour and compares against exact MILP)
python algorithm/heuristics/nearest_neighbour.py data/coordinates_20_cities.xlsx

# 2-Opt Local Search (edge-reversal refinement from a Nearest Neighbour tour)
python algorithm/heuristics/two_opt.py data/coordinates_20_cities.xlsx

# 3-Opt Local Search (triplet reconnection refinement from a Nearest Neighbour tour)
python algorithm/heuristics/three_opt.py data/coordinates_20_cities.xlsx

# Branch and Bound (exact solver with pruning for small instances, e.g. n <= 10)
python algorithm/exact/branch_and_bound.py data/coordinates_10_cities.xlsx

# Metaheuristics (runs Simulated Annealing & Ant Colony Optimization with MILP baseline)
python algorithm/metaheuristics/metaheuristic.py data/coordinates_20_cities.xlsx
python algorithm/metaheuristics/metaheuristic.py data/coordinates_80_cities.xlsx --no-exact
```

---

### Interactive Visualizers

The repository provides graphical tools for interactive examination of tour progression and state spaces:

- **Constructive & Local Search Visualizers (Click-Through Step-by-Step)**:
  Interactive Matplotlib windows stepping through individual greedy choices or accepted edge swaps:
  ```bash
  python algorithm/heuristics/nearest_neighbour_visualization.py data/coordinates_10_cities.xlsx
  python algorithm/heuristics/two_opt_visualization.py data/coordinates_10_cities.xlsx
  python algorithm/heuristics/three_opt_visualization.py data/coordinates_10_cities.xlsx
  ```

- **Brute-Force Permutation Visualizer**:
  Animated circular layout demonstrating factorial permutation space in real time:
  ```bash
  python algorithm/exact/brute_force_visualized.py
  ```
  *(Enter a distance matrix containing "London", e.g. `data/distances_20_cities.xlsx`. For $n > 10$, this serves as a live demonstration of factorial explosion—close the window when done observing.)*

- **Simulated Annealing Animated Visualizer & GIF Exporter**:
  Real-time multi-panel visualization of temperature decay, tour untangling, and distance convergence:
  ```bash
  # Live interactive GUI on the default 80-city dataset
  python algorithm/metaheuristics/simulated_annealing_visualized.py

  # Start from a Nearest Neighbour seed instead of a random route
  python algorithm/metaheuristics/simulated_annealing_visualized.py data/coordinates_80_cities.xlsx --nn-seed

  # Export animation directly to GIF (use --frames 60 for fast generation)
  python algorithm/metaheuristics/simulated_annealing_visualized.py data/coordinates_80_cities.xlsx --save-gif outputs/charts/sa_80_cities.gif --frames 60
  ```
  *Key arguments: `--save-gif [PATH]` (headless GIF export), `--frames N` (frame count), `--nn-seed` (seed with NN tour), `--iter N` (iteration budget).*

---

## Output Reports

All execution scripts automatically save formatted Markdown (`.md`) reports into the dedicated [`outputs/`](outputs/) directory (e.g. `outputs/tsp_loader_coordinates_80_cities_results.md`).

Each individual algorithm report includes:
- **Route Quality**: Final distance, theoretical shortest distance (via HiGHS MILP), percentage of optimum, and distance excess.
- **Efficiency Metrics**: Execution times, candidate examination counts, complete pass counts ($p$), and accepted moves.
- **Complexity Analysis**: Theoretical operation-count formulas and Big-O notation.
- **Complete Tour Itineraries**: Numbered, step-by-step city visiting orders for both the heuristic route and the proven optimal tour.

The orchestrator (`tsp_loader.py`) also writes side-by-side comparison tables across all algorithms into `outputs/tsp_loader_<dataset>_results.md`. Because every algorithm is run multiple times (see `--runs`), each report contains:

- **Performance & Quality Summary**: one row per algorithm. Distance and gap vs optimum come from the **best run**; time is the **mean** over all runs.
- **Runtime Statistics** (all algorithms): min, mean, max and standard deviation (SD) of the runtime.
- **Distance Statistics** (non-deterministic algorithms only - Simulated Annealing and Ant Colony Optimization): min, mean, max and SD of the final tour distance, the mean gap vs the optimum, and the **optimum hit rate** (how many runs, e.g. `7/10`, reached the proven optimum; `N/A` when run with `--no-exact`).
- **Visual Charts**:
  - **Runtime Performance**: Horizontal bar chart on a logarithmic scale showing mean execution time with min–max error bars for every algorithm.
  - **Tour Distance Performance**: Grouped horizontal bar chart showing the best (minimum), mean, and worst (maximum) tour distance for each algorithm, alongside a reference line for the proven MILP optimum.
- **Full Tour Itineraries**: the best-run route for each algorithm, with its runtime mean ± SD.

### Cross-Dataset Scalability Summary (`outputs/tsp_loader_scalability_summary.md`)

When multiple datasets of different city counts are evaluated in a run, `tsp_loader.py` also writes a combined scalability report featuring cross-problem line graphs:
- **Runtime vs. Number of Cities**: Multi-line graph (logarithmic runtime scale) showing how execution time scales from small to large instances for each algorithm.
- **Best Result vs. Number of Cities**: Multi-line graph displaying the percentage gap above the proven optimum ($(\text{distance} / \text{optimum} - 1) \times 100\%$) across all problem sizes. Methods that run only on small instances (Brute Force, Branch and Bound) are rendered as individual benchmark points.
- **Summary Comparison Tables**: Side-by-side runtime and solution-quality tables across all evaluated city counts.

All chart images are automatically generated via Matplotlib and saved to [`outputs/charts/`](outputs/charts).


### NOTE 

 - **Reproducibility & Statistics:** Non-deterministic algorithms (Simulated Annealing and Ant Colony Optimization) vary their seed on each run (`--seed + i`), while deterministic algorithms return the same tour every run. Each algorithm executes an untimed warm-up run first to eliminate initialization overhead.
 - **2-Opt / 3-Opt Timing:** Includes Nearest Neighbour construction time because refinement requires a valid initial tour.
 - **Raw Data Export:** Every timed run is exported to `outputs/tsp_loader_<dataset>_runs.csv` (columns: `algorithm, deterministic, run, seed, distance, time_sec`) for analysis in pandas or Excel. Warm-up runs are excluded.