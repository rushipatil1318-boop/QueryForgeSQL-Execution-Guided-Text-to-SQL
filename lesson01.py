"""Reference exercise: compare complete rows while preserving duplicates."""

from collections import Counter


def bag_equal(predicted: list[tuple], reference: list[tuple]) -> bool:
    """Ignore row order, but require identical duplicate counts."""
    return Counter(predicted) == Counter(reference)
