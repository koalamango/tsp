# TSP Algorithms Reference

[← Back to Main Repository Guide](../README.md)

## Overview

Given a list of cities and the distances between each pair, the Travelling Salesperson Problem asks: *What is the shortest possible route that visits each city exactly once and returns to the origin city?*

Because TSP is NP-hard, exact approaches become intractable as the number of cities $n$ grows. This repository demonstrates how different algorithmic paradigms balance computational complexity, execution time, and solution quality:

1. **Exact Solvers** guarantee the global optimum for small to moderate problem instances (pure brute-force permutation search up to $n \le 12$, Held-Karp dynamic programming up to $n \le 20$, and HiGHS MILP benchmark baselines).
2. **Approximation Algorithms** provide provable theoretical performance bounds (e.g., Christofides' 1.5-approximation) in polynomial time.
3. **Heuristics** rapidly generate good solutions (e.g., within milliseconds for $n = 20$).
4. **Local Search** iteratively eliminates route crossings and suboptimal connections.
5. **Metaheuristics** escape local optima to discover near-optimal solutions on larger graphs.

## Implemented Algorithms

### 1. Exact Methods

- **Dynamic Programming — Held-Karp Algorithm (`algorithm/exact/dynamic_programming/held_karp.py` & `held_karp_visualized.py`)**:
  - Solves the TSP to exact global optimality using the Bellman-Held-Karp dynamic programming formulation with bitmask subset states: `cost_matrix[subset][city]`.
  - Achieves a time complexity of $O(n^2 2^n)$ and memory of $O(n 2^n)$, making exact solutions feasible for moderate graphs ($n \le 20$) where exhaustive search ($O((n-1)!)$) becomes computationally impossible.
  - Accompanied by an interactive visualizer (`held_karp_visualized.py`) animating the optimal tour construction step-by-step.

- **Brute-Force Permutation Search (`algorithm/exact/brute_force/brute_force.py` & `algorithm/exact/brute_force_visualized.py`)**:
  - Evaluates all $(n - 1)!$ permutations starting and ending at a fixed depot city (e.g., London).
  - Features real-time animated plotting in Matplotlib, displaying current route evaluations, best-so-far distances, and the final optimal tour, as well as a headless runner (`run_brute_force`) used by `tsp_loader.py`.
  - Demonstrates the factorial explosion of exhaustive search ($n = 12$ requires checking 39.9M routes in ~110 seconds without pruning).

- **HiGHS Mixed-Integer Linear Programming (`scipy.optimize.milp`)**:
  - Embedded in `algorithm/heuristics/nearest_neighbour.py` and `algorithm/heuristics/three_opt.py` as an exact ground-truth solver.
  - Employs the Dantzig-Fulkerson-Johnson (DFJ) formulation with dynamic subtour-elimination cuts.
  - Proves the true global optimum ($\text{MIP gap} = 0.0$) to benchmark heuristic accuracy.

### 2. Approximation Algorithms

- **Christofides Algorithm (`algorithm/approximation/christofides.py`)**:
  - Polynomial-time approximation algorithm guaranteeing a solution at most $1.5$ times the optimal tour length on metric TSP instances satisfying the triangle inequality.
  - Operates in $O(n^3)$ time through 5 systematic graph phases:
    1. Computes a Minimum Spanning Tree (MST) of the metric graph.
    2. Identifies the subset of vertices with odd degree in the MST.
    3. Computes a minimum-weight perfect matching among the odd-degree vertices.
    4. Combines the MST and matching edges to form an Eulerian multigraph.
    5. Traces an Eulerian tour and shortcuts previously visited vertices to construct a valid Hamiltonian cycle.
  - Implemented cleanly with standard CSV input handling and Matplotlib route plotting.

### 3. Constructive Heuristics

- **Nearest Neighbour (`algorithm/heuristics/nearest_neighbour.py`)**:
  - Greedily extends the tour by choosing the closest unvisited city at each step until a full cycle is formed.
  - Runs in $O(n^2)$ time with exactly $n(n - 1) / 2$ candidate-distance examinations.
  - Automatically compares against the exact MILP solution and outputs an audit report (`outputs/<input>_nearest_neighbour_results.md`).
  - Includes an interactive step-by-step visualizer (`algorithm/heuristics/nearest_neighbour_visualization.py`).

### 4. Local Search & Improvement Heuristics

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

### 5. Metaheuristics

- **Simulated Annealing (`algorithm/metaheuristics/metaheuristic.py` & `algorithm/metaheuristics/simulated_annealing_visualized.py`)**:
  - Probabilistic technique based on thermal annealing.
  - Uses geometric cooling ($T_{k+1} = \alpha \cdot T_k$) and the Metropolis acceptance criterion ($\Delta < 0$ or $P < e^{-\Delta / T}$).
  - Employs a hybrid neighborhood operator: 70% 2-opt segment reversals and 30% 2-city swaps.
  - Includes an animated multi-panel visualizer (`algorithm/metaheuristics/simulated_annealing_visualized.py`) with live route evolution, distance convergence, and cooling curves.

- **Ant Colony Optimization (ACO) (`algorithm/metaheuristics/metaheuristic.py`)**:
  - Nature-inspired population metaheuristic (Ant System).
  - Uses pheromone trails ($\tau_{ij}$) and distance visibility ($\eta_{ij} = 1 / d_{ij}$).
  - Artificial ants construct tours stochastically based on transition probabilities $P_{ij} \propto (\tau_{ij})^\alpha \cdot (\eta_{ij})^\beta$, followed by pheromone evaporation and deposit reinforcement.

## Algorithm Complexity & Comparison Matrix

| Algorithm | Paradigm | Time Complexity | Space Complexity | Optimality Guarantee | Recommended Problem Size |
|:---|:---|:---:|:---:|:---:|:---|
| **Brute Force** | Exact / Exhaustive | $O((n - 1)!)$ | $O(n)$ | Global Optimum ($0.0\%$ gap) | $n \le 12$ |
| **Held-Karp DP** | Exact / Dynamic Programming | $O(n^2 2^n)$ | $O(n 2^n)$ | Global Optimum ($0.0\%$ gap) | $n \le 20$ |
| **HiGHS MILP (DFJ)** | Exact / Mathematical Programming | Exponential (worst case) | $O(n^2)$ | Global Optimum within tolerance | $n \le 50$ (moderate runtime) |
| **Christofides** | Approximation (Metric TSP) | $O(n^3)$ | $O(n^2)$ | $\le 1.5 \times \text{OPT}$ guarantee | $n \ge 1,000$ |
| **Nearest Neighbour** | Greedy Constructive | $O(n^2)$ | $O(n)$ | None (heuristic) | $n > 10,000$ (sub-second) |
| **2-Opt (from NN)** | Local Search | $O(p \cdot n^2)$ | $O(n)$ | 2-optimal (local minimum) | $n \le 1,000$ |
| **3-Opt (from NN)** | Local Search | $O(p \cdot n^3)$ | $O(n)$ | 3-optimal (local minimum) | $n \le 200$ |
| **Simulated Annealing** | Metaheuristic | $O(k \cdot n)$ | $O(n)$ | Asymptotically optimal / near-opt | Scales to large $n$ |
| **Ant Colony (ACO)** | Metaheuristic | $O(I \cdot m \cdot n^2)$ | $O(n^2)$ | Near-optimal heuristic | Scales to large $n$ |


