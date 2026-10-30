-- One row per order and touch: every session the buyer had in the lookback window before the purchase, up to and
-- including the purchasing session, in order. Sessions before 1 Nov 2020 aren't in the sample, so early paths are
-- truncated at the start (left-censored).
select
    o.order_id,
    o.revenue_usd,
    s.session_key,
    s.channel,
    s.session_start_at,
    datediff('second', s.session_start_at, o.purchased_at) / 86400.0                  as days_before_purchase,
    row_number() over (partition by o.order_id order by s.session_start_at, s.session_key)   as touch_no,
    count(*) over (partition by o.order_id)                                             as path_length
from {{ ref('fct_orders') }} o
join {{ ref('fct_sessions') }} s
    on s.user_id = o.user_id
   and s.session_start_at <= o.purchased_at
   and s.session_start_at >= o.purchased_at - interval '{{ var("lookback_days") }} days'
