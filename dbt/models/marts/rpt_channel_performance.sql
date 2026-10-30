-- Sessions, users, engagement, conversion and revenue by channel (revenue credited to the purchasing session).
select
    channel,
    count(*)                                                    as sessions,
    count(distinct user_id)                                     as users,
    round(avg(is_engaged::int), 4)                              as engagement_rate,
    sum(orders)                                                 as orders,
    round(sum(orders) / count(*), 5)                            as orders_per_session,
    round(sum(revenue_usd), 2)                                  as revenue_usd,
    round(sum(revenue_usd) / count(*), 3)                       as revenue_per_session_usd
from {{ ref('fct_sessions') }}
group by 1
