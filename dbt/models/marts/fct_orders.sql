-- One row per order. In this obfuscated export, 906 purchase events have no transaction id and some ids repeat across
-- users, so an order is a purchase event per user, transaction id and amount, with exact repeats removed (the same
-- user, id and amount logged more than once). Purchases without an id stay as separate orders.
with purchases as (
    select
        session_key,
        user_id,
        transaction_id,
        coalesce(revenue_usd, 0)                                                    as revenue_usd,
        event_at,
        row_number() over (
            partition by user_id, coalesce(transaction_id, cast(event_at as varchar)), coalesce(revenue_usd, 0)
            order by event_at)                                                      as copy_no
    from {{ ref('stg_ga4__events') }}
    where event_name = 'purchase'
)

select
    md5(user_id || '|' || coalesce(transaction_id, cast(event_at as varchar)) || '|' || revenue_usd) as order_id,
    session_key,
    user_id,
    transaction_id,
    event_at                                                                        as purchased_at,
    revenue_usd
from purchases
where copy_no = 1
