"""Load the GA4 sample into DuckDB (bronze.ga4_events).

Source: Google's public GA4 obfuscated sample of the Google Merchandise Store (Nov 2020 - Jan 2021), as flattened
to one row per event by the Hugging Face dataset gizdevans/ga4-bq-flattened-data. The flattened file repeats its
header row inside the data (31 times); those rows are dropped and counted. Types are cast here, values unchanged.

Usage: python ingestion/load_ga4.py --csv data/raw/ga4_flattened.csv --db warehouse/marketing.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

COLUMNS = """
    strptime(event_date, '%Y%m%d')::date                                as event_date,
    event_name,
    make_timestamp(cast(event_timestamp as bigint))                     as event_at,
    user_pseudo_id,
    make_timestamp(try_cast(user_first_touch_timestamp as bigint))      as user_first_touch_at,
    device_category,
    country,
    traffic_source                                                      as user_first_source,
    traffic_medium                                                      as user_first_medium,
    traffic_campaign                                                    as user_first_campaign,
    ep_source                                                           as event_source,
    ep_medium                                                           as event_medium,
    ep_campaign                                                         as event_campaign,
    cast(ga_session_id as bigint)                                       as ga_session_id,
    try_cast(ga_session_number as integer)                              as ga_session_number,
    try_cast(engagement_time_msec as bigint)                            as engagement_time_msec,
    try_cast(session_engaged as integer)                                as session_engaged,
    ecom_transaction_id                                                 as transaction_id,
    try_cast(ecom_revenue_usd as double)                                as revenue_usd,
    page_location
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=Path("data/raw/ga4_flattened.csv"))
    ap.add_argument("--db", default="warehouse/marketing.duckdb")
    args = ap.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists bronze")
    src = f"read_csv('{args.csv.as_posix()}', header = true, all_varchar = true)"
    headers = con.execute(f"select count(*) from {src} where event_date = 'event_date'").fetchone()[0]
    con.execute(f"create or replace table bronze.ga4_events as select {COLUMNS} from {src} where event_date <> 'event_date'")
    n, users, first, last = con.execute(
        "select count(*), count(distinct user_pseudo_id), min(event_date), max(event_date) from bronze.ga4_events").fetchone()
    print(f"bronze.ga4_events: {n:,} events, {users:,} users, {first} to {last}; dropped {headers} repeated header rows")


if __name__ == "__main__":
    main()
