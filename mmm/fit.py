"""Fit a marketing mix model: revenue = baseline + sum over channels of beta x hill(adstock(spend)).

Variable projection: for any choice of the non-linear media parameters (decay, half-saturation, shape per channel),
the baseline and media coefficients are linear, so they are solved exactly with non-negative least squares (media
can't have a negative effect). A global search (differential evolution, fixed seed) chooses the non-linear
parameters that minimise the squared error. Uncertainty comes from a moving-block bootstrap of the residuals,
refitting from the point estimate each time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution, minimize, nnls

from .core import adstock, hill

DECAY = (0.0, 0.9)
K_MULT = (0.2, 3.0)     # half-saturation as a multiple of the channel's mean adstocked spend
SHAPE = (0.5, 3.0)


def baseline_matrix(df: pd.DataFrame) -> np.ndarray:
    t = np.arange(len(df))
    cols = [np.ones(len(df)), t / len(df)]
    for h in (1, 2):
        cols += [np.sin(2 * np.pi * h * t / 52), np.cos(2 * np.pi * h * t / 52)]
    cols += [df["promo"].to_numpy(), df["bfcm"].to_numpy()]
    return np.column_stack(cols)


@dataclass
class Fit:
    channels: list[str]
    params: np.ndarray            # (channels, 3): decay, k, shape
    coef_base: np.ndarray
    beta: np.ndarray
    fitted: np.ndarray
    sse: float


def _design(df, channels, theta):
    feats, ks = [], []
    for i, c in enumerate(channels):
        decay, kmult, s = theta[3 * i: 3 * i + 3]
        ad = adstock(df[f"spend_{c}"].to_numpy(float), decay)
        k = kmult * ad[ad > 0].mean()
        feats.append(hill(ad, k, s))
        ks.append(k)
    return np.column_stack(feats), ks


def _solve(df, channels, theta, y, base):
    media, ks = _design(df, channels, theta)
    scale = y.std()
    # baseline columns may take either sign: split each into + and - parts for NNLS
    X = np.column_stack([base, -base, media * scale])
    coef, _ = nnls(X / scale, y / scale, maxiter=5000)
    nb = base.shape[1]
    coef_base = coef[:nb] - coef[nb:2 * nb]
    beta = coef[2 * nb:] * scale
    fitted = base @ coef_base + media @ beta
    return coef_base, beta, fitted, ks


def fit(df: pd.DataFrame, channels: list[str], y: np.ndarray | None = None, start: np.ndarray | None = None,
        seed: int = 7, lift_tests: dict[str, tuple[float, float]] | None = None, noise_var: float | None = None) -> Fit:
    """lift_tests calibrates the model with experiments: {channel: (measured ROI, standard error)}. Each adds a
    penalty ((model ROI - measured ROI) / se)^2 to the squared error scaled by the noise variance, the
    likelihood-style weighting a Bayesian MMM gives an experiment prior."""
    y = df["revenue"].to_numpy(float) if y is None else y
    base = baseline_matrix(df)
    spend = {c: df[f"spend_{c}"].to_numpy(float).sum() for c in channels}

    def sse(theta):
        _, beta, fitted, _ = _solve(df, channels, theta, y, base)
        err = float(((y - fitted) ** 2).sum())
        if lift_tests:
            media, _ = _design(df, channels, theta)
            for i, c in enumerate(channels):
                if c in lift_tests:
                    m, se = lift_tests[c]
                    model_roi = beta[i] * media[:, i].sum() / spend[c]
                    err += noise_var * ((model_roi - m) / se) ** 2
        return err

    bounds = [DECAY, K_MULT, SHAPE] * len(channels)
    if start is None:
        res = differential_evolution(sse, bounds, seed=seed, maxiter=120, popsize=18, tol=1e-7, polish=True)
    else:
        res = minimize(sse, start, bounds=bounds, method="L-BFGS-B")
    coef_base, beta, fitted, ks = _solve(df, channels, res.x, y, base)
    params = np.array([[res.x[3 * i], ks[i], res.x[3 * i + 2]] for i in range(len(channels))])
    return Fit(channels, params, coef_base, beta, fitted, float(((y - fitted) ** 2).sum()))


def contributions(df: pd.DataFrame, f: Fit) -> pd.DataFrame:
    out = {}
    for i, c in enumerate(f.channels):
        decay, k, s = f.params[i]
        out[c] = f.beta[i] * hill(adstock(df[f"spend_{c}"].to_numpy(float), decay), k, s)
    return pd.DataFrame(out, index=df.index)


def roi(df: pd.DataFrame, f: Fit) -> dict[str, float]:
    contrib = contributions(df, f)
    return {c: float(contrib[c].sum() / df[f"spend_{c}"].sum()) for c in f.channels}


def predict(df: pd.DataFrame, f: Fit) -> np.ndarray:
    return baseline_matrix(df) @ f.coef_base + contributions(df, f).sum(axis=1).to_numpy()


def bootstrap_roi(df: pd.DataFrame, f: Fit, n: int = 40, block: int = 8, seed: int = 11,
                  lift_tests: dict | None = None, noise_var: float | None = None) -> pd.DataFrame:
    """Moving-block bootstrap of residuals (keeps autocorrelation), refitting from the point estimate. With lift
    tests, each draw also redraws the experiments' measured ROI from their standard errors."""
    rng = np.random.default_rng(seed)
    resid = df["revenue"].to_numpy(float) - f.fitted
    start = np.concatenate([[p[0], p[1] / _mean_ad(df, c, p[0]), p[2]] for c, p in zip(f.channels, f.params)])
    rows = []
    for b in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, len(df) - block, len(df) // block + 1)])[: len(df)]
        y_b = f.fitted + resid[idx]
        tests_b = {c: (rng.normal(m, se), se) for c, (m, se) in lift_tests.items()} if lift_tests else None
        fb = fit(df, f.channels, y=y_b, start=np.clip(start, [lo for lo, _ in [DECAY, K_MULT, SHAPE] * len(f.channels)],
                                                       [hi for _, hi in [DECAY, K_MULT, SHAPE] * len(f.channels)]),
                 lift_tests=tests_b, noise_var=noise_var)
        rows.append({"draw": b, **roi(df, fb)})
    return pd.DataFrame(rows)


def _mean_ad(df, c, decay):
    ad = adstock(df[f"spend_{c}"].to_numpy(float), decay)
    return ad[ad > 0].mean()
