# TSP Benchmark Results: Cartesian coordinates (10 Cities) - coordinates_10_cities.xlsx

- **Cities Evaluated:** 10 (London, Bristol, Birmingham, Manchester, Liverpool, Leeds, Sheffield, Nottingham, Cardiff, Oxford)
- **Timestamp:** 2026-11-10 22:13:59
- **Runs per algorithm:** 10 (plus 1 untimed warm-up run each)
- **Base seed:** 42 (Simulated Annealing / Ant Colony run *i* uses seed + *i*)
- **Simulated Annealing parameters:** t_init=393.16, alpha=0.999137, max_iter=8,000 (scaled to n = 10)

## Performance & Quality Summary

Distance and gap are from the **best run**; time is the **mean** over all runs.

| Algorithm | Distance (best run) | Mean Time (s) | Gap vs Opt | Route Summary |
| --- | --- | --- | --- | --- |
| Exact MILP (HiGHS) | 837.25 | 0.002083 | 0.00% (proven) | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| Nearest Neighbour | 1,176.82 | 0.000005 | +40.56% | London -> Leeds -> Birmingham -> ... -> Oxford -> Cardiff -> London |
| 2-Opt (from NN) † | 837.25 | 0.000023 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| 3-Opt (from NN) † | 837.25 | 0.000118 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| Simulated Annealing | 837.25 | 0.007844 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| Ant Colony Opt. | 837.25 | 0.041180 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| Brute Force (10 cities) | 837.25 | 0.188383 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |
| Branch and Bound (10 cities) | 837.25 | 0.011294 | +0.00% | London -> Leeds -> Birmingham -> ... -> Bristol -> Oxford -> London |

† Time includes building the Nearest Neighbour starting tour (2-Opt and 3-Opt cannot run without it), i.e. NN time + refinement time.

## Runtime Statistics (All Algorithms)

| Algorithm | Min (s) | Mean (s) | Max (s) | SD (s) |
| --- | --- | --- | --- | --- |
| Exact MILP (HiGHS) | 0.001967 | 0.002083 | 0.002807 | 0.000256 |
| Nearest Neighbour | 0.000004 | 0.000005 | 0.000006 | 0.000000 |
| 2-Opt (from NN) † | 0.000020 | 0.000023 | 0.000026 | 0.000002 |
| 3-Opt (from NN) † | 0.000115 | 0.000118 | 0.000123 | 0.000003 |
| Simulated Annealing | 0.007721 | 0.007844 | 0.007951 | 0.000069 |
| Ant Colony Opt. | 0.040922 | 0.041180 | 0.041433 | 0.000167 |
| Brute Force (10 cities) | 0.187478 | 0.188383 | 0.191186 | 0.001188 |
| Branch and Bound (10 cities) | 0.011105 | 0.011294 | 0.011457 | 0.000123 |

† Time includes building the Nearest Neighbour starting tour (2-Opt and 3-Opt cannot run without it), i.e. NN time + refinement time.

## Distance Statistics (Non-Deterministic Algorithms)

Final tour distance over 10 runs, each with a different seed. *Optimum Hit Rate* is the number of runs that reached the proven optimum (N/A when the exact solver was skipped).

| Algorithm | Min | Mean | Max | SD | Mean Gap vs Opt | Optimum Hit Rate |
| --- | --- | --- | --- | --- | --- | --- |
| Simulated Annealing | 837.25 | 837.25 | 837.25 | 0.00 | +0.00% | 10/10 |
| Ant Colony Opt. | 837.25 | 837.25 | 837.25 | 0.00 | +0.00% | 10/10 |

## Charts

### Runtime per Algorithm

![Runtime per algorithm: mean with min-max whiskers, log scale](charts/tsp_loader_coordinates_10_cities_runtime.png)

### Tour Distance per Algorithm (Best / Mean / Worst)

![Best, mean and worst tour distance per algorithm](charts/tsp_loader_coordinates_10_cities_distance.png)

Deterministic algorithms return the same tour every run, so their best, mean and worst bars are identical.

† Time includes building the Nearest Neighbour starting tour (2-Opt and 3-Opt cannot run without it), i.e. NN time + refinement time.

## Full Tour Itineraries

### Exact MILP (HiGHS)
- **Final Distance:** 837.25
- **Runtime:** 0.002083 ± 0.000256 seconds (mean ± SD over 10 runs; min 0.001967, max 0.002807)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### Nearest Neighbour
- **Final Distance:** 1,176.82
- **Runtime:** 0.000005 ± 0.000000 seconds (mean ± SD over 10 runs; min 0.000004, max 0.000006)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> Cardiff -> London`

### 2-Opt (from NN) †
- **Final Distance:** 837.25
- **Runtime:** 0.000023 ± 0.000002 seconds (mean ± SD over 10 runs; min 0.000020, max 0.000026)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### 3-Opt (from NN) †
- **Final Distance:** 837.25
- **Runtime:** 0.000118 ± 0.000003 seconds (mean ± SD over 10 runs; min 0.000115, max 0.000123)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### Simulated Annealing
- **Final Distance (best run):** 837.25
- **Runtime:** 0.007844 ± 0.000069 seconds (mean ± SD over 10 runs; min 0.007721, max 0.007951)
- **Distance over 10 runs:** min 837.25 / mean 837.25 / max 837.25 (SD 0.00)
- **Full Tour Itinerary (best run):**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### Ant Colony Opt.
- **Final Distance (best run):** 837.25
- **Runtime:** 0.041180 ± 0.000167 seconds (mean ± SD over 10 runs; min 0.040922, max 0.041433)
- **Distance over 10 runs:** min 837.25 / mean 837.25 / max 837.25 (SD 0.00)
- **Full Tour Itinerary (best run):**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### Brute Force (10 cities)
- **Final Distance:** 837.25
- **Runtime:** 0.188383 ± 0.001188 seconds (mean ± SD over 10 runs; min 0.187478, max 0.191186)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

### Branch and Bound (10 cities)
- **Final Distance:** 837.25
- **Runtime:** 0.011294 ± 0.000123 seconds (mean ± SD over 10 runs; min 0.011105, max 0.011457)
- **Full Tour Itinerary:**
  `London -> Leeds -> Birmingham -> Manchester -> Cardiff -> Sheffield -> Nottingham -> Liverpool -> Bristol -> Oxford -> London`

## Method Notes
- **Exact MILP (HiGHS):** Proves global optimum via DFJ subtour-elimination constraints (`scipy.optimize.milp`).
- **Nearest Neighbour:** Greedy heuristic choosing closest unvisited city ($O(n^2)$).
- **2-Opt & 3-Opt:** Iterative edge-swap local search refining the Nearest Neighbour route. Their runtimes include building that route.
- **Simulated Annealing & Ant Colony:** Stochastic metaheuristics for escaping local optima. Simulated Annealing iterations scale as max(8000, 50·n²) with a data-calibrated start temperature.
- **Branch & Bound:** Prunes partial tours as soon as cumulative cost exceeds known upper bound.
- **Brute Force:** Evaluates all $(n - 1)!$ permutations.
- **Deterministic algorithms** (everything except Simulated Annealing and Ant Colony) return the same tour every run; only their runtime varies.
- **Warm-up:** each algorithm is run once before timing starts and that run is discarded, so one-off start-up costs do not skew the statistics.
