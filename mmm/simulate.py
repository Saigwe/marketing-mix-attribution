"""SIMULATED weekly marketing data with known truth, so a marketing mix model can be scored.

GA4 records sessions and revenue but not media spend, and no public dataset pairs real spend with a known true
return. So the mix model is tested the way a model should be: on data where the answer is known.

Three years (156 weeks) of revenue for an online store with:
  baseline     trend, yearly seasonality, a Black Friday / Cyber Monday spike and a price-promotion control
  4 channels   paid search, paid social, display and online video, each with its own carry-over (adstock decay),
               diminishing returns (Hill curve) and true return on spend. Spend is flighted in bursts, heavier in
               Q4, and search and social move together (correlation about 0.5), as they do in real plans.
  noise        5% of mean revenue

The truth (parameters, weekly contributions, ROI per channel) is written beside the data and read only by the
evaluation, never by the model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .core import adstock, hill

SEED = 2024
WEEKS = 156
CHANNELS = {  # mean weekly spend, decay, half-saturation (x mean adstocked spend), shape, target ROI
    "paid_search": (24_000, 0.20, 0.9, 1.2, 2.4),
    "paid_social": (18_000, 0.45, 1.1, 1.6, 1.5),
    "display":     (12_000, 0.30, 1.4, 1.3, 0.6),
    "online_video": (15_000, 0.70, 0.8, 2.0, 1.1),
}


LIFT_TESTS = {"paid_social": 0.25, "online_video": 0.30}   # channel: standard error of the experiment's ROI


def lift_tests(truth: dict, seed: int = SEED + 1) -> dict[str, tuple[float, float]]:
    """Geo lift experiments on two channels, as a marketing team would run: each measures the channel's true ROI
    with sampling error (its standard error), so the measured value is not the truth."""
    rng = np.random.default_rng(seed)
    return {c: (round(float(rng.normal(truth["channels"][c]["roi"], se)), 3), se) for c, se in LIFT_TESTS.items()}


def simulate(seed: int = SEED) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    t = np.arange(WEEKS)
    week = pd.date_range("2022-01-03", periods=WEEKS, freq="W-MON")
    season = 1 + 0.18 * np.sin(2 * np.pi * (t - 10) / 52) + 0.08 * np.cos(4 * np.pi * t / 52)
    q4 = np.isin(week.month, [10, 11, 12]).astype(float)
    bfcm = ((week.month == 11) & (week.day >= 21)).astype(float)
    promo = (rng.random(WEEKS) < 0.12).astype(float)
    baseline = (220_000 + 450 * t) * season + 120_000 * bfcm + 35_000 * promo

    shared = rng.normal(0, 1, WEEKS)
    spend, truth, contrib = {}, {}, {}
    for name, (mean, decay, k_mult, s, roi) in CHANNELS.items():
        on = rng.random(WEEKS) < (0.55 if name == "online_video" else 0.85)       # flighting
        z = 0.7 * shared + 0.7 * rng.normal(0, 1, WEEKS) if name in ("paid_search", "paid_social") else rng.normal(0, 1, WEEKS)
        x = mean * on * np.exp(0.35 * z) * (1 + 0.6 * q4)
        x = np.round(np.maximum(x, 0), -1)
        ad = adstock(x, decay)
        k = k_mult * ad[ad > 0].mean()
        shape = hill(ad, k, s)
        beta = roi * x.sum() / shape.sum()           # scale so the channel's true ROI over 3 years equals the target
        spend[name] = x
        contrib[name] = beta * shape
        truth[name] = {"decay": decay, "half_saturation": round(float(k), 2), "shape": s, "beta": round(float(beta), 2),
                       "spend": float(x.sum()), "contribution": float(contrib[name].sum()),
                       "roi": float(contrib[name].sum() / x.sum())}

    noise = rng.normal(0, 0.05 * baseline.mean(), WEEKS)
    revenue = baseline + sum(contrib.values()) + noise
    df = pd.DataFrame({"week": week, "revenue": np.round(revenue, 2), "promo": promo, "bfcm": bfcm,
                       **{f"spend_{c}": v for c, v in spend.items()}})
    truth_all = {"channels": truth, "baseline_share": float(baseline.sum() / revenue.sum()),
                 "weekly_contribution": {c: np.round(v, 2).tolist() for c, v in contrib.items()}}
    return df, truth_all
