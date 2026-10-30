"""Markov attribution on the GA4 journeys, combined with the five rule-based models from dbt.

Converting journeys: each order's touches in the lookback window (silver.int_conversion_paths).
Non-converting journeys: every session sequence of users who never bought in the sample.

Usage: python -m attribution.run --db warehouse/marketing.duckdb --out results
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from .markov import attribute, removal_effects


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse/marketing.duckdb")
    ap.add_argument("--out", type=Path, default=Path("results"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db, read_only=True)

    conv = con.execute("""select order_id, list(channel order by touch_no) from main_silver.int_conversion_paths group by 1""").fetchall()
    nonconv = con.execute("""
        select user_id, list(channel order by session_start_at, session_key)
        from main_gold.fct_sessions
        where user_id not in (select user_id from main_gold.fct_orders)
        group by 1""").fetchall()
    paths = [(list(p), True) for _, p in conv] + [(list(p), False) for _, p in nonconv]
    orders, revenue = con.execute("select count(*), sum(revenue_usd) from main_gold.fct_orders").fetchone()

    effects = removal_effects(paths)
    by_orders = attribute(paths, orders)
    by_revenue = attribute(paths, revenue)
    markov = pd.DataFrame({"model": "markov", "channel": list(effects),
                           "attributed_orders": [round(by_orders[c], 4) for c in effects],
                           "attributed_revenue_usd": [round(by_revenue[c], 2) for c in effects]})
    rules = con.execute("select model, channel, attributed_orders, attributed_revenue_usd from main_gold.rpt_attribution_rules").df()
    allm = pd.concat([rules, markov], ignore_index=True)
    allm["revenue_share"] = allm["attributed_revenue_usd"] / allm.groupby("model")["attributed_revenue_usd"].transform("sum")
    allm.sort_values(["model", "channel"]).to_csv(args.out / "attribution_by_model.csv", index=False)

    wide = allm.pivot(index="channel", columns="model", values="revenue_share").round(4)
    wide = wide[["last_click", "last_non_direct_click", "first_click", "linear", "position_based", "time_decay", "markov"]]
    wide.to_csv(args.out / "attribution_revenue_share.csv")

    lengths = con.execute("select path_length, count(*) from (select order_id, max(path_length) as path_length from main_silver.int_conversion_paths group by 1) group by 1 order by 1").fetchall()
    summary = {
        "converting_journeys": len(conv), "non_converting_journeys": len(nonconv),
        "orders": orders, "revenue_usd": round(revenue, 2),
        "single_touch_share": round(sum(n for l, n in lengths if l == 1) / len(conv), 4),
        "removal_effects": {c: round(e, 4) for c, e in sorted(effects.items(), key=lambda kv: -kv[1])},
    }
    (args.out / "attribution_summary.json").write_text(json.dumps(summary, indent=2))
    print(wide.to_string())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
