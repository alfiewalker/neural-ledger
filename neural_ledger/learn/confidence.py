"""Confidence and uncertainty computation for links.

Uncertainty is derived from the variance of observed feedback evidence.
A link whose evidence is consistently positive (e.g., [1, 1, 0.9]) has
low variance → low uncertainty → high confidence.

A link that has received conflicting signals (e.g., [1, 0, 1, 0]) has
high variance → high uncertainty → low confidence.
"""

from __future__ import annotations

import math


def compute_uncertainty(evidence: list[float]) -> float:
    """Return uncertainty in [0, 1] based on variance of evidence values.

    - Zero evidence → maximum uncertainty (0.5, a conservative prior).
    - One sample → moderate uncertainty (cannot estimate variance properly).
    - Many consistent samples → near 0.
    - Many conflicting samples → near 1.
    """
    n = len(evidence)
    if n == 0:
        return 0.5
    if n == 1:
        # Single data point: uncertainty reflects distance from neutral.
        return 0.5 - abs(evidence[0] - 0.5)

    mean = sum(evidence) / n
    variance = sum((x - mean) ** 2 for x in evidence) / n
    # Variance of a Bernoulli is at most 0.25.  Normalise to [0, 1].
    uncertainty = min(variance / 0.25, 1.0)
    return uncertainty


def compute_confidence(evidence: list[float]) -> float:
    """Confidence is the complement of uncertainty."""
    return 1.0 - compute_uncertainty(evidence)
