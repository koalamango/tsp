"""
tsp_utils.py - Shared formatting and Markdown report helpers for TSP algorithms.
"""
from __future__ import annotations

from typing import Optional, Sequence


def pluralize(count: int, word: str = "run") -> str:
    """Format a count and singular/plural noun, e.g. '1 run' or '10 runs'."""
    return f"{count} {word}{'' if count == 1 else 's'}"


def format_duration(seconds: float, compact: bool = False) -> str:
    """Format a duration in seconds into a human-readable string."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:.0f} µs" if compact else f"{seconds * 1e6:.1f} microseconds"
    if seconds < 1.0:
        return f"{seconds * 1e3:.1f} ms" if compact else f"{seconds * 1000:.2f} ms"
    if seconds < 60.0 or compact:
        return f"{seconds:.2f} s" if compact else f"{seconds:.2f} seconds"
    if seconds < 3600.0:
        return f"{seconds / 60:.1f} minutes"
    if seconds < 86400.0:
        return f"{seconds / 3600:.1f} hours"
    if seconds < 365.25 * 86400.0:
        return f"{seconds / 86400:.1f} days"
    years = seconds / (365.25 * 86400.0)
    if years < 1e6:
        return f"{years:,.1f} years"
    if years < 1e9:
        return f"{years / 1e6:,.2f} million years"
    return f"{years / 1e9:,.2f} billion years"


def format_gap(
    distance: float,
    opt_distance: Optional[float],
    default: str = "N/A",
    precision: int = 2,
    zero_label: Optional[str] = None,
) -> str:
    """Format percentage gap relative to optimal distance."""
    if opt_distance is None or opt_distance <= 0:
        return default
    gap = (distance / opt_distance - 1.0) * 100.0
    if zero_label is not None and gap <= 0:
        return zero_label
    return f"{gap:+.{precision}f}%"


def markdown_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    alignments: Optional[Sequence[str]] = None,
) -> str:
    """Render a GitHub-flavoured Markdown table."""
    sep = list(alignments) if alignments is not None else ["---"] * len(headers)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)
