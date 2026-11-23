"""README charts from results/attribution_revenue_share.csv and results/mmm_roi_vs_truth.csv.
Usage: python charts/make_charts.py"""
import csv
import sys
from pathlib import Path

import numpy as np

import style as st
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results"
OUT = ROOT / "docs" / "charts"


def read(name):
    with open(RES / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


share = read("attribution_revenue_share.csv")
models = ["last_click", "last_non_direct_click", "first_click", "linear", "position_based", "time_decay", "markov"]
labels = ["Last click", "Last non-direct", "First click", "Linear", "Position", "Time decay", "Markov"]
share.sort(key=lambda r: -float(r["markov"]))
grid = np.array([[float(r[m]) for m in models] for r in share])
f, ax = st.fig(8, 3.9)
cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd"] + st.SEQ)
ax.imshow(grid, cmap=cmap, aspect="auto", vmin=0, vmax=0.45)
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        v = grid[i, j]
        ax.text(j, i, f"{v:.0%}" if v >= 0.005 else "<1%", ha="center", va="center", fontsize=8.5,
                color="white" if v > 0.28 else st.TEXT)
ax.set_xticks(range(len(models)), labels)
ax.set_yticks(range(len(share)), [r["channel"] for r in share])
ax.grid(False)
st.head(ax, "Direct's share of revenue swings from 14% to 39% depending on the model",
        "Share of $340,647 of real GA4 revenue credited to each channel, by attribution model")
st.save(f, OUT / "attribution_by_model.png")

roi = read("mmm_roi_vs_truth.csv")
ch = ["paid_search", "paid_social", "display", "online_video"]
names = ["Paid search", "Paid social", "Display", "Online video"]
f, ax = st.fig(8, 3.6)
for k, (model, col, dy) in enumerate([("observational", st.S[1], -0.15), ("calibrated", st.S[0], 0.15)]):
    rows = {r["channel"]: r for r in roi if r["model"] == model}
    for i, c in enumerate(ch):
        r = rows[c]
        ax.plot([float(r["roi_90_low"]), float(r["roi_90_high"])], [i + dy] * 2, color=col, lw=2, solid_capstyle="round")
        ax.plot(float(r["estimated_roi"]), i + dy, "o", color=col, ms=6, label=model.capitalize() + " MMM, 90% interval" if i == 0 else None)
for i, c in enumerate(ch):
    t = float(next(r for r in roi if r["channel"] == c)["true_roi"])
    ax.plot([t, t], [i - 0.35, i + 0.35], color=st.TEXT, lw=1.6, label="True ROI (simulated)" if i == 0 else None)
ax.set_yticks(range(4), names)
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.set_xlabel("Return on ad spend")
st.head(ax, "Calibrating to lift tests pulls the ROI estimates toward the truth",
        "Mean ROI error 0.61 observational, 0.16 calibrated. Simulated spend with a known answer", legend=True, ncol=3)
st.save(f, OUT / "mmm_roi_vs_truth.png")
print(f"wrote charts to {OUT}")
