"""Simulate, fit, validate and optimise; write results/. The truth is used only to score the models.

Two models are fitted to the same data:
  observational   revenue and spend alone
  calibrated      the same model, also matched to two geo lift experiments (paid social, online video)

Usage: python -m mmm.run --out results [--bootstrap 40]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .fit import bootstrap_roi, contributions, fit, predict, roi  # noqa: E402
from .optimise import optimise, weekly_revenue  # noqa: E402
from .simulate import CHANNELS, lift_tests, simulate  # noqa: E402

HOLDOUT = 26


def evaluate(name, df, channels, truth, n_boot, tests=None, noise_var=None):
    train = df.iloc[:-HOLDOUT].reset_index(drop=True)
    f_train = fit(train, channels, lift_tests=tests, noise_var=noise_var)
    pred = predict(df, f_train)
    mape = float(np.mean(np.abs(pred[-HOLDOUT:] - df["revenue"].iloc[-HOLDOUT:]) / df["revenue"].iloc[-HOLDOUT:]))

    f = fit(df, channels, lift_tests=tests, noise_var=noise_var)
    est = roi(df, f)
    boot = bootstrap_roi(df, f, n=n_boot, lift_tests=tests, noise_var=noise_var)
    contrib = contributions(df, f)
    rows = []
    for i, c in enumerate(channels):
        t = truth["channels"][c]
        lo, hi = np.percentile(boot[c], [5, 95])
        rows.append({"model": name, "channel": c, "true_roi": round(t["roi"], 3), "estimated_roi": round(est[c], 3),
                     "roi_90_low": round(float(lo), 3), "roi_90_high": round(float(hi), 3),
                     "truth_inside_interval": bool(lo <= t["roi"] <= hi),
                     "abs_error": round(abs(est[c] - t["roi"]), 3),
                     "true_decay": t["decay"], "estimated_decay": round(float(f.params[i][0]), 3)})

    current = {c: float(df[f"spend_{c}"].mean()) for c in channels}
    fitted_curves = {c: (float(f.params[i][0]), float(f.params[i][1]), float(f.params[i][2]), float(f.beta[i]))
                     for i, c in enumerate(channels)}
    true_curves = {c: (truth["channels"][c]["decay"], truth["channels"][c]["half_saturation"],
                       truth["channels"][c]["shape"], truth["channels"][c]["beta"]) for c in channels}
    plan = optimise(fitted_curves, current)
    best = optimise(true_curves, current)
    now, got, ideal = (weekly_revenue(true_curves, a) for a in (current, plan, best))
    summary = {
        "holdout_mape": round(mape, 4),
        "in_sample_r2": round(1 - f.sse / float(((df["revenue"] - df["revenue"].mean()) ** 2).sum()), 4),
        "estimated_media_share": round(float(contrib.to_numpy().sum() / df["revenue"].sum()), 4),
        "mean_abs_roi_error": round(float(np.mean([r["abs_error"] for r in rows])), 3),
        "truth_inside_90pct_interval": sum(r["truth_inside_interval"] for r in rows),
        "roi_rank_order_correct": [r["channel"] for r in sorted(rows, key=lambda r: r["true_roi"])]
                                  == [r["channel"] for r in sorted(rows, key=lambda r: r["estimated_roi"])],
        "plan": {c: round(v) for c, v in plan.items()},
        "model_predicted_uplift_per_week": round(weekly_revenue(fitted_curves, plan) - weekly_revenue(fitted_curves, current)),
        "true_uplift_per_week": round(got - now),
        "share_of_possible_uplift_captured": round((got - now) / (ideal - now), 3),
    }
    return rows, summary, f, pred, current, best, now, ideal


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--bootstrap", type=int, default=40)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    channels = list(CHANNELS)
    df, truth = simulate()
    tests = lift_tests(truth)
    df.to_csv(args.out / "mmm_weekly_data.csv", index=False)

    rows_o, sum_o, f_o, pred_o, current, best, now, ideal = evaluate("observational", df, channels, truth, args.bootstrap)
    noise_var = f_o.sse / (len(df) - 4 * len(channels) - 8)
    rows_c, sum_c, f_c, pred_c, *_ = evaluate("calibrated", df, channels, truth, args.bootstrap, tests, noise_var)

    pd.DataFrame(rows_o + rows_c).to_csv(args.out / "mmm_roi_vs_truth.csv", index=False)
    summary = {
        "weeks": len(df), "holdout_weeks": HOLDOUT, "bootstrap_draws": args.bootstrap,
        "true_media_share": round(1 - truth["baseline_share"], 4),
        "lift_tests": {c: {"measured_roi": m, "standard_error": se, "true_roi": round(truth["channels"][c]["roi"], 3)}
                       for c, (m, se) in tests.items()},
        "weekly_budget": round(sum(current.values())),
        "current_allocation": {c: round(v) for c, v in current.items()},
        "true_best_allocation": {c: round(v) for c, v in best.items()},
        "true_media_revenue_per_week": {"current": round(now), "true_best": round(ideal)},
        "observational": sum_o, "calibrated": sum_c,
    }
    (args.out / "mmm_summary.json").write_text(json.dumps(summary, indent=2))
    (args.out / "mmm_truth.json").write_text(json.dumps(truth["channels"], indent=2))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["week"], df["revenue"], lw=1.2, color="#333", label="revenue (simulated)")
    ax.plot(df["week"], pred_o, lw=1, label="observational model, fitted on first 130 weeks")
    ax.plot(df["week"], pred_c, lw=1, label="calibrated model, fitted on first 130 weeks")
    ax.axvline(df["week"].iloc[-HOLDOUT], color="grey", ls="--", lw=0.8)
    ax.set_title("Weekly revenue and holdout forecasts (last 26 weeks right of the line)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out / "mmm_holdout.png", dpi=110)
    print(pd.DataFrame(rows_o + rows_c).to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
