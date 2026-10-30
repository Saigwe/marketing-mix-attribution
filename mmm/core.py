"""Media response building blocks shared by the simulator and the model.

adstock   geometric carry-over: this week's effective spend = spend + decay x last week's effective spend
hill      diminishing returns: x^s / (x^s + k^s), from 0 to 1, half-saturated at x = k
"""
from __future__ import annotations

import numpy as np


def adstock(spend: np.ndarray, decay: float) -> np.ndarray:
    out = np.empty_like(spend, dtype=float)
    carry = 0.0
    for t, x in enumerate(spend):
        carry = x + decay * carry
        out[t] = carry
    return out


def hill(x: np.ndarray, k: float, s: float) -> np.ndarray:
    x = np.maximum(x, 0.0)
    return x ** s / (x ** s + k ** s)


def response(spend: np.ndarray, decay: float, k: float, s: float, beta: float) -> np.ndarray:
    """Weekly revenue contribution of one channel."""
    return beta * hill(adstock(spend, decay), k, s)


def steady_state_response(weekly_spend: np.ndarray | float, decay: float, k: float, s: float, beta: float):
    """Weekly contribution once a constant weekly spend has run long enough for carry-over to settle."""
    return beta * hill(np.asarray(weekly_spend, dtype=float) / (1 - decay), k, s)
