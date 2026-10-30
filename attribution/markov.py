"""Data-driven attribution with a first-order Markov chain and removal effects.

Every journey is a path of channels from (start) to (conversion) or (null). Transition probabilities are counted
from all journeys, converting and not. A channel's removal effect is the share of conversions lost if that channel
disappeared (journeys reaching it go to (null) instead). Credit is shared in proportion to removal effects, so it
reflects what each channel adds across journeys, not just where it sits.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

START, CONV, NULL = "(start)", "(conversion)", "(null)"


def transitions(paths: list[tuple[list[str], bool]]) -> tuple[list[str], np.ndarray]:
    """paths: (channels in order, converted?). Returns the state list and a row-stochastic transition matrix."""
    counts = Counter()
    for channels, converted in paths:
        seq = [START, *channels, CONV if converted else NULL]
        counts.update(zip(seq[:-1], seq[1:]))
    channels = sorted({c for p, _ in paths for c in p})
    states = [START, *channels, CONV, NULL]
    idx = {s: i for i, s in enumerate(states)}
    m = np.zeros((len(states), len(states)))
    for (a, b), n in counts.items():
        m[idx[a], idx[b]] += n
    m[idx[CONV], idx[CONV]] = m[idx[NULL], idx[NULL]] = 1     # absorbing
    rows = m.sum(axis=1, keepdims=True)
    return states, np.divide(m, rows, out=np.zeros_like(m), where=rows > 0)


def conversion_probability(states: list[str], m: np.ndarray, removed: str | None = None) -> float:
    """Probability of being absorbed in (conversion) from (start), optionally with one channel removed."""
    m = m.copy()
    idx = {s: i for i, s in enumerate(states)}
    if removed is not None:
        r = idx[removed]
        m[:, idx[NULL]] += m[:, r]
        m[:, r] = 0
        m[r, :] = 0
        m[r, idx[NULL]] = 1
    transient = [i for s, i in idx.items() if s not in (CONV, NULL)]
    q = m[np.ix_(transient, transient)]
    b = m[np.ix_(transient, [idx[CONV]])]
    absorb = np.linalg.solve(np.eye(len(transient)) - q, b)
    return float(absorb[transient.index(idx[START]), 0])


def removal_effects(paths: list[tuple[list[str], bool]]) -> dict[str, float]:
    states, m = transitions(paths)
    base = conversion_probability(states, m)
    return {s: 1 - conversion_probability(states, m, removed=s) / base for s in states if s not in (START, CONV, NULL)}


def attribute(paths: list[tuple[list[str], bool]], total: float) -> dict[str, float]:
    """Share `total` (orders or revenue) across channels in proportion to removal effects."""
    effects = removal_effects(paths)
    s = sum(effects.values())
    return {c: total * e / s for c, e in effects.items()}
