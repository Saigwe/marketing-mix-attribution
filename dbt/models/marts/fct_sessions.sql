-- One row per session with its channel, funnel steps and the orders and revenue it closed.
select
    s.*,
    coalesce(o.orders, 0)           as orders,
    coalesce(o.revenue_usd, 0)      as revenue_usd
from {{ ref('int_ga4__sessions') }} s
left join (
    select session_key, count(*) as orders, sum(revenue_usd) as revenue_usd
    from {{ ref('fct_orders') }}
    group by 1
) o using (session_key)
