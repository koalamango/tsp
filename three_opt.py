"""
Author: Richard Clark

Keep this file beside the latest nearest_neighbour.py.

Run: py three_opt.py "C:/path/cities.xlsx"
Dependencies: py -m pip install openpyxl scipy
Creates an NN starting route, improves it with 3-opt, and writes a Markdown
report into the outputs folder. Rerunning replaces this algorithm's report.
"""
import sys
from pathlib import Path
from time import perf_counter

from nearest_neighbour import (
    build_euclidean_matrix,
    read_cities,
    nearest_neighbour,
    route_length,
    exact_route,
)
from tsp_utils import markdown_table


def reconnect(tour, i, j, k, case):
    """Reconnect the three segments; keep city 0 as the starting city."""
    first = tour[i + 1:j + 1]
    second = tour[j + 1:k + 1]
    third = tour[k + 1:] + tour[:i + 1]
    arrangements = [
        (first[::-1], second),
        (first, second[::-1]),
        (first[::-1], second[::-1]),
        (second, first),
        (second[::-1], first),
        (second, first[::-1]),
        (second[::-1], first[::-1]),
    ]
    left, right = arrangements[case]
    result = third + left + right
    start = result.index(0)
    return result[start:] + result[:start]


def three_opt(route, distances):
    """Best-improvement 3-opt for symmetric distances.

    Test seven reconnections of every triple of distinct tour edges.
    Include 2-opt-equivalent cases and adjacent cuts; some tests duplicate
    the same resulting tour, but every tested reconnection is counted.
    Evaluate each change in O(1); rebuild only the accepted route in O(n).
    """
    tour = route[:-1].copy()  # Remove the repeated starting city.
    n = len(tour)
    checks = passes = moves = 0
    while True:
        passes += 1
        best_change, best_move = -1e-10, None
        for i in range(n - 2):
            for j in range(i + 1, n - 1):
                for k in range(j + 1, n):
                    a, b = tour[i], tour[i + 1]
                    c, d = tour[j], tour[j + 1]
                    e, f = tour[k], tour[(k + 1) % n]
                    old = distances[a][b] + distances[c][d] + distances[e][f]
                    # Same order as the seven arrangements in reconnect().
                    new_costs = (
                        distances[a][c] + distances[b][d] + distances[e][f],
                        distances[a][b] + distances[c][e] + distances[d][f],
                        distances[a][c] + distances[b][e] + distances[d][f],
                        distances[a][d] + distances[e][b] + distances[c][f],
                        distances[a][e] + distances[d][b] + distances[c][f],
                        distances[a][d] + distances[e][c] + distances[b][f],
                        distances[a][e] + distances[d][c] + distances[b][f],
                    )
                    for case, cost in enumerate(new_costs):
                        checks += 1
                        change = cost - old
                        if change < best_change:
                            best_change = change
                            best_move = (i, j, k, case)
        if best_move is None:
            return tour + [0], checks, passes, moves
        tour = reconnect(tour, *best_move)
        moves += 1


def main(file_path):
    cities, points = read_cities(file_path)
    n = len(cities)
    distances = build_euclidean_matrix(points)

    start = perf_counter()
    route, nn_checks = nearest_neighbour(distances)
    nn_seconds = perf_counter() - start
    initial_distance = route_length(route, distances)

    start = perf_counter()
    route, checks, passes, moves = three_opt(route, distances)
    opt_seconds = perf_counter() - start
    final_distance = route_length(route, distances)

    print('Finding and proving the shortest route...')
    start = perf_counter()
    optimal_route = exact_route(distances)
    optimal_distance = route_length(optimal_route, distances)
    exact_seconds = perf_counter() - start
    if optimal_distance > 0:
        percent = f'{100 * final_distance / optimal_distance:.4f}%'
        excess = f'{100 * (final_distance / optimal_distance - 1):.4f}%'
    else:
        percent = excess = 'Undefined (optimum is zero)'

    quality = [
        ('Initial nearest-neighbour distance', f'{initial_distance:.6f}'),
        ('Final 3-opt distance', f'{final_distance:.6f}'),
        ('Shortest possible distance', f'{optimal_distance:.6f}'),
        ('Final distance as % of shortest', percent),
        ('Distance above optimum', excess),
    ]
    efficiency = [
        ('NN execution time', f'{nn_seconds:.9f} seconds'),
        ('3-opt refinement time', f'{opt_seconds:.9f} seconds'),
        ('Combined heuristic time', f'{nn_seconds + opt_seconds:.9f} seconds'),
        ('NN candidate-distance examinations', f'{nn_checks:,}'),
        ('3-opt reconnection examinations', f'{checks:,}'),
        ('3-opt complete passes (p)', f'{passes:,}'),
        ('Accepted improvement moves', f'{moves:,}'),
        ('NN operation-count formula', 'n(n-1)/2'),
        ('3-opt reconnection-count formula', '7*p*n(n-1)(n-2)/6'),
        ('NN time complexity', 'O(n^2)'),
        ('3-opt time complexity', 'O(p*n^3)'),
        ('Combined time complexity', 'O(n^2 + p*n^3)'),
    ]
    lines = [
        '# Nearest neighbour + 3-opt results',
        '',
        f'**Input:** {Path(file_path).name}',
        '',
        f'**Cities:** {n}',
        '',
        '## Route quality',
        '',
        markdown_table(['Measure', 'Value'], [[label, value] for label, value in quality], ['---', '---:']),
        '',
        '100% means optimal; 110% means 10% longer than optimal.',
        '',
        "Distances are straight-line distances in the coordinates' units.",
        '',
        '## Efficiency',
        '',
        markdown_table(['Measure', 'Value'], [[label, value] for label, value in efficiency]),
    ]
    lines += ['', '## Interpretation', '',
              '- Times are single-run wall-clock measurements and vary by machine.',
              '- Heuristic timings exclude Excel reading, matrix construction, '
              'exact search and report writing.',
              '- Counts measure candidate examinations, not every Python operation.',
              '- Each pass tests all n(n-1)(n-2)/6 triples and seven reconnections '
              'per triple; duplicate resulting tours are still counted.',
              '- p includes the final pass, which finds no improvement. '
              'It depends on the input; accepted moves = p - 1.',
              '- Rebuilding an accepted route costs O(n), dominated by the O(n^3) scan.',
              '- The matrix uses O(n^2) memory; auxiliary route storage uses O(n).',
              '- All seven reconnections are included, including 2-opt-equivalent moves.',
              '- A local optimum is not necessarily a global optimum. '
              'Starting from NN, 3-opt need not beat a separately run NN + 2-opt.', '',
              '## Exact reference', '',
              f'- Reference time, including model construction: {exact_seconds:.6f} seconds.',
              '- Method: HiGHS MILP with subtour-elimination cuts.',
              '- Status: optimal to solver numerical tolerances; requested relative MIP gap = 0.',
              '- Distances are not rounded before solving. Exact search has no time limit '
              'and can dominate the total runtime.', '',
              '## Final visiting order', '']
    lines += [f'{step}. {cities[city]}' for step, city in enumerate(route, 1)]
    lines += ['', '## Optimal visiting order', '']
    lines += [f'{step}. {cities[city]}' for step, city in enumerate(optimal_route, 1)]
    spreadsheet = Path(file_path)
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output = outputs_dir / f'{spreadsheet.stem}_three_opt_results.md'
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Results saved to: {output.resolve()}')


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else input('Excel file path: ').strip().strip('"')
    main(path)
