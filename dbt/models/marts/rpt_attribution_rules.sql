-- Revenue credit by channel under five rule-based attribution models. Every model hands out each order's revenue
-- exactly once (a test checks it). The data-driven Markov model is computed in attribution/markov.py.
--   last_click                 all credit to the purchasing session's channel
--   last_non_direct_click      the last touch that wasn't Direct (Direct if there was nothing else), as GA's
--                              cross-channel last click does
--   first_click                all credit to the first touch in the lookback window
--   linear                     equal credit to every touch
--   position_based             40% first, 40% last, 20% shared by the middle (50/50 for two touches)
--   time_decay                 credit halves for every {{ var('time_decay_half_life') }} days before the purchase
with p as (
    select
        *,
        max(case when channel <> 'Direct' then touch_no end) over (partition by order_id) as last_non_direct_no,
        power(0.5, days_before_purchase / {{ var('time_decay_half_life') }})            as decay_weight
    from {{ ref('int_conversion_paths') }}
),

weights as (
    select
        order_id, revenue_usd, channel,
        (touch_no = path_length)::double                                                   as last_click,
        (touch_no = coalesce(last_non_direct_no, path_length))::double                     as last_non_direct_click,
        (touch_no = 1)::double                                                             as first_click,
        1.0 / path_length                                                                  as linear,
        case
            when path_length = 1 then 1.0
            when path_length = 2 then 0.5
            when touch_no in (1, path_length) then 0.4
            else 0.2 / (path_length - 2)
        end                                                                                as position_based,
        decay_weight / sum(decay_weight) over (partition by order_id)                      as time_decay
    from p
),

long as (
    unpivot weights on last_click, last_non_direct_click, first_click, linear, position_based, time_decay
    into name model value credit
)

select
    model,
    channel,
    round(sum(credit), 4)                       as attributed_orders,
    round(sum(credit * revenue_usd), 2)         as attributed_revenue_usd
from long
group by 1, 2
