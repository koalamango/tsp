# TSP Scalability Summary

- **Timestamp:** 2026-11-10 22:14:33
- **Runs per algorithm:** 10 (plus 1 untimed warm-up run each)
- **Base seed:** 42
- **Datasets:**
  - **10 cities:** [Cartesian coordinates (10 Cities) - coordinates_10_cities.xlsx](tsp_loader_coordinates_10_cities_results.md)
  - **20 cities:** [Cartesian coordinates (20 Cities) - coordinates_20_cities.xlsx](tsp_loader_coordinates_20_cities_results.md)
  - **40 cities:** [Cartesian coordinates (40 Cities) - coordinates_40_cities.xlsx](tsp_loader_coordinates_40_cities_results.md)
  - **80 cities:** [Cartesian coordinates (80 Cities) - coordinates_80_cities.xlsx](tsp_loader_coordinates_80_cities_results.md)

## Runtime vs Number of Cities

![Mean runtime vs number of cities](charts/tsp_loader_scalability_runtime.png)

Mean runtime in seconds (log scale). 2-Opt and 3-Opt times include building the Nearest Neighbour starting tour.

| Algorithm | 10 cities | 20 cities | 40 cities | 80 cities |
| --- | --- | --- | --- | --- |
| Exact MILP (HiGHS) | 0.002083 | 0.004597 | 0.063850 | 0.114235 |
| Nearest Neighbour | 0.000005 | 0.000014 | 0.000049 | 0.000186 |
| 2-Opt (from NN) | 0.000023 | 0.000081 | 0.000386 | 0.004169 |
| 3-Opt (from NN) | 0.000118 | 0.001940 | 0.016665 | 0.411133 |
| Simulated Annealing | 0.007844 | 0.020130 | 0.082433 | 0.325594 |
| Ant Colony Opt. | 0.041180 | 0.123457 | 0.412126 | 1.450870 |
| Brute Force | 0.188383 | - | - | - |
| Branch and Bound | 0.011294 | - | - | - |

## Best Result vs Number of Cities

![Best result vs number of cities](charts/tsp_loader_scalability_gap.png)

| Algorithm | 10 cities | 20 cities | 40 cities | 80 cities |
| --- | --- | --- | --- | --- |
| Exact MILP (HiGHS) | +0.00% | +0.00% | +0.00% | +0.00% |
| Nearest Neighbour | +40.56% | +33.02% | +8.50% | +30.66% |
| 2-Opt (from NN) | +0.00% | +2.90% | +1.98% | +6.47% |
| 3-Opt (from NN) | +0.00% | +2.90% | +0.97% | +2.56% |
| Simulated Annealing | +0.00% | +0.00% | +0.00% | +0.21% |
| Ant Colony Opt. | +0.00% | +0.00% | +1.19% | +3.22% |
| Brute Force | +0.00% | - | - | - |
| Branch and Bound | +0.00% | - | - | - |

> [!NOTE]
> Raw tour distances are not comparable between datasets of different sizes, so the best result is shown as the gap (%) above the proven optimum. Brute Force and Branch and Bound only run on the smallest dataset, so they appear as a single marker.
