"""
Author: Jessie W

Metaheuristic TSP algorithms: Simulated Annealing and Ant Colony Optimization.
"""
import time
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# 1. DATA LOADER (Compatible with Excel or Grid)

def load_distance_excel(path: str, sheet_name: int = 0) -> Tuple[List[str], List[List[float]]]:
    """Loads symmetric distance matrix from team's Excel template."""
    df = pd.read_excel(path, sheet_name=sheet_name, index_col=0)
    df.columns = [str(c).strip() for c in df.columns]
    df.index = [str(i).strip() for i in df.index]
    cities = list(df.columns)
    n = len(cities)
    dist_matrix = [[0.0] * n for _ in range(n)]

    for i, a in enumerate(cities):
        for j, b in enumerate(cities):
            val = df.loc[a, b]
            if a != b and not pd.isna(val):
                d = float(val)
                dist_matrix[i][j] = d
                dist_matrix[j][i] = d
    return cities, dist_matrix

def calculate_route_distance(route: List[int], dist_matrix: List[List[float]]) -> float:
    """Calculates total closed-loop TSP distance."""
    n = len(route)
    return sum(dist_matrix[route[i]][route[(i + 1) % n]] for i in range(n))

# 2. SIMULATED ANNEALING (SA)

def solve_tsp_sa(
    dist_matrix: List[List[float]],
    t_init: float = 500.0,
    alpha: float = 0.997,
    max_iter: int = 8000,
    seed: int = None
) -> Dict:
    """Solves TSP using Simulated Annealing with hybrid 2-opt and swap neighbourhoods."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    n = len(dist_matrix)
    curr_route = [0] + random.sample(range(1, n), n - 1)
    curr_dist = calculate_route_distance(curr_route, dist_matrix)
    best_route, best_dist = list(curr_route), curr_dist

    temp = t_init
    history = []
    conv_iter = 0
    t_start = time.perf_counter()

    for it in range(1, max_iter + 1):
        i, j = sorted(random.sample(range(1, n), 2))
        if random.random() < 0.7:
            # 2-opt segment reversal (untangles crossing paths)
            candidate = curr_route[:i] + curr_route[i:j + 1][::-1] + curr_route[j + 1:]
        else:
            # 2-city swap
            candidate = list(curr_route)
            candidate[i], candidate[j] = candidate[j], candidate[i]

        cand_dist = calculate_route_distance(candidate, dist_matrix)
        delta = cand_dist - curr_dist

        # Metropolis acceptance criterion
        if delta < 0 or random.random() < np.exp(-delta / temp):
            curr_route, curr_dist = candidate, cand_dist
            if curr_dist < best_dist:
                best_route, best_dist = list(curr_route), curr_dist
                conv_iter = it

        temp *= alpha
        history.append(best_dist)

    exec_time = time.perf_counter() - t_start
    return {
        "route": best_route,
        "distance": best_dist,
        "time_sec": exec_time,
        "history": history,
        "convergence_iter": conv_iter
    }

# 3. ANT COLONY OPTIMISATION (ACO)

def solve_tsp_aco(
    dist_matrix: List[List[float]],
    n_ants: int = 20,
    n_iter: int = 150,
    alpha: float = 1.0,
    beta: float = 3.0,
    evaporation: float = 0.1,
    q_deposit: float = 100.0,
    seed: int = None
) -> Dict:
    """Solves TSP using Ant Colony Optimisation (Ant System)."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    n = len(dist_matrix)
    pheromone = np.full((n, n), 0.1)
    heuristic = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j and dist_matrix[i][j] > 0:
                heuristic[i][j] = 1.0 / dist_matrix[i][j]

    best_route, best_dist = [], float("inf")
    history = []
    conv_iter = 0
    t_start = time.perf_counter()

    for it in range(1, n_iter + 1):
        all_routes, all_dists = [], []
        for _ in range(n_ants):
            curr = 0
            visited = {0}
            route = [0]
            while len(visited) < n:
                unvisited = [j for j in range(n) if j not in visited]
                weights = [
                    (pheromone[curr][j] ** alpha) * (heuristic[curr][j] ** beta)
                    for j in unvisited
                ]
                nxt = random.choices(unvisited, weights=weights, k=1)[0]
                route.append(nxt)
                visited.add(nxt)
                curr = nxt

            d = calculate_route_distance(route, dist_matrix)
            all_routes.append(route)
            all_dists.append(d)
            if d < best_dist:
                best_route, best_dist = list(route), d
                conv_iter = it

        # Pheromone update: evaporation + new deposits
        pheromone *= (1.0 - evaporation)
        for route, d in zip(all_routes, all_dists):
            deposit = q_deposit / d
            for k in range(n):
                u, v = route[k], route[(k + 1) % n]
                pheromone[u][v] += deposit
                pheromone[v][u] += deposit

        history.append(best_dist)

    exec_time = time.perf_counter() - t_start
    return {
        "route": best_route,
        "distance": best_dist,
        "time_sec": exec_time,
        "history": history,
        "convergence_iter": conv_iter
    }