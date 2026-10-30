"""Budget optimiser: reallocate the same total weekly budget across channels to maximise revenue.

Uses steady-state response curves (constant weekly spend, carry-over settled). Each channel may move between 50%
and 150% of its historical average, a guardrail any media plan would have.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .core import steady_state_response


def optimise(curves: dict[str, tuple[float, float, float, float]], current: dict[str, float],
             low: float = 0.5, high: float = 1.5) -> dict[str, float]:
    names = list(current)
    x0 = np.array([current[c] for c in names])
    total = x0.sum()

    def neg_revenue(x):
        return -sum(steady_state_response(x[i], *curves[c]) for i, c in enumerate(names))

    res = minimize(neg_revenue, x0, method="SLSQP", bounds=[(low * v, high * v) for v in x0],
                   constraints=[{"type": "eq", "fun": lambda x: x.sum() - total}], options={"ftol": 1e-9, "maxiter": 500})
    return {c: float(res.x[i]) for i, c in enumerate(names)}


def weekly_revenue(curves: dict[str, tuple[float, float, float, float]], allocation: dict[str, float]) -> float:
    return float(sum(steady_state_response(v, *curves[c]) for c, v in allocation.items()))
