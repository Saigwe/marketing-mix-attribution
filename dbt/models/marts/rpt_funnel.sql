-- The purchase funnel: sessions reaching each step, overall, by device and by channel, with conversion from the step
-- before. A session counts at a step if it reached that step, whatever it skipped.
with steps as (
    select 1 as step_order, 'session' as step union all
    select 2, 'view_item' union all select 3, 'add_to_cart' union all select 4, 'begin_checkout' union all
    select 5, 'add_shipping_info' union all select 6, 'add_payment_info' union all select 7, 'purchase'
),

flags as (
    select
        device_category,
        channel,
        unnest([1, 2, 3, 4, 5, 6, 7])                                           as step_order,
        unnest([true, viewed_item, added_to_cart, began_checkout, added_shipping, added_payment, purchased]) as reached
    from {{ ref('fct_sessions') }}
),

counted as (
    select device_category, channel, step_order, count(*) filter (where reached) as sessions
    from flags
    group by grouping sets ((step_order), (device_category, step_order), (channel, step_order))
)

select
    case when device_category is not null then 'device' when channel is not null then 'channel' else 'all' end as cut,
    coalesce(device_category, channel, 'All sessions')                           as segment,
    c.step_order,
    s.step,
    c.sessions,
    round(c.sessions / lag(c.sessions) over (partition by cut, segment order by c.step_order), 4)   as conversion_from_previous,
    round(c.sessions / first_value(c.sessions) over (partition by cut, segment order by c.step_order), 5) as share_of_sessions
from counted c
join steps s using (step_order)
