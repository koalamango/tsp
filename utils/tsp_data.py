"""
Author: Jessie W

Utilities for loading our data files
"""

from pathlib import Path
import math
from typing import List, Tuple, Union

import pandas as pd
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_data_path(path: Union[str, Path]) -> Path:
    """Resolve a dataset path, searching local directory, PROJECT_ROOT, and PROJECT_ROOT/data."""
    resolved = Path(path)
    if resolved.exists():
        return resolved
    for candidate in (PROJECT_ROOT / path, PROJECT_ROOT / "data" / path):
        if candidate.exists():
            return candidate
    return resolved


def read_cities(file_path: Union[str, Path]) -> Tuple[List[str], List[Tuple[float, float]]]:
    """Read city names and (X, Y) coordinates from an Excel workbook with City, X, Y columns."""
    resolved_path = resolve_data_path(file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"TSP data file not found: {file_path}")

    workbook = load_workbook(resolved_path, read_only=True, data_only=True)
    try:
        sheet = (
            workbook["Cities"]
            if "Cities" in workbook.sheetnames
            else workbook.worksheets[0]
        )
        rows = iter(sheet.values)
        header = next(rows, ())

        if [str(v).strip().lower() for v in header[:3]] != ["city", "x", "y"]:
            raise ValueError("The first three columns must be City, X, Y.")

        cities, points = [], []

        for row in rows:
            if all(v is None for v in row[:3]):
                continue

            name, x, y = row[:3]

            if name is None or not str(name).strip() or x is None or y is None:
                raise ValueError("Each city needs a name and two coordinates.")

            point = (float(x), float(y))

            if not all(math.isfinite(v) for v in point):
                raise ValueError("Coordinates must be finite numbers.")

            cities.append(str(name))
            points.append(point)

        if len(cities) < 2:
            raise ValueError("At least two cities are required.")

        return cities, points
    finally:
        workbook.close()


def build_euclidean_matrix(points: List[Tuple[float, float]]) -> List[List[float]]:
    """Build a symmetric Euclidean distance matrix from (X, Y) coordinates."""
    return [
        [math.dist(a, b) for b in points]
        for a in points
    ]


def load_distance_excel(
    path: Union[str, Path],
    sheet_name: Union[int, str] = 0,
) -> Tuple[List[str], List[List[float]]]:
    """Load symmetric distance matrix from an Excel sheet."""
    resolved_path = resolve_data_path(path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"TSP distance matrix file not found: {path}")

    df = pd.read_excel(resolved_path, sheet_name=sheet_name, index_col=0)
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


def load_tsp_data(
    path: Union[str, Path],
    sheet_name: Union[int, str] = 0,
) -> Tuple[List[str], List[List[float]], str]:
    """
    Auto-detects and loads either Cartesian coordinates (City, X, Y)
    or symmetric distance matrices from an Excel file.

    Returns (cities, dist_matrix, dataset_type), where dataset_type is
    'Cartesian coordinates' or 'Symmetric distance matrix'.
    """
    resolved_path = resolve_data_path(path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"TSP data file not found: {path}")

    try:
        cities, points = read_cities(resolved_path)
        return cities, build_euclidean_matrix(points), "Cartesian coordinates"
    except ValueError:
        cities, dist_matrix = load_distance_excel(resolved_path, sheet_name=sheet_name)
        return cities, dist_matrix, "Symmetric distance matrix"


def load_coordinates_or_matrix(
    file_path: Union[str, Path],
    sheet_name: Union[int, str] = 0,
) -> Tuple[List[str], List[Tuple[float, float]], List[List[float]], str, str]:
    """Load city names, 2D plotting coordinates, and distance matrix from Excel.

    Uses read_cities for Cartesian coordinate sheets; falls back to load_distance_excel
    with a circular node layout for symmetric distance matrices.

    Returns:
      (cities, points_xy, dist_matrix, xlabel, ylabel)
    """
    resolved_path = resolve_data_path(file_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"TSP data file not found: {file_path}")

    try:
        cities, points_xy = read_cities(resolved_path)
        dist_matrix = build_euclidean_matrix(points_xy)
        return cities, points_xy, dist_matrix, "X Coordinate", "Y Coordinate"
    except ValueError:
        cities, dist_matrix = load_distance_excel(resolved_path, sheet_name=sheet_name)
        n = len(cities)
        points_xy = [
            (math.cos(math.pi / 2 - 2 * math.pi * i / n) * 100.0,
             math.sin(math.pi / 2 - 2 * math.pi * i / n) * 100.0)
            for i in range(n)
        ]
        return cities, points_xy, dist_matrix, "Circular X", "Circular Y"
