-- One row per session. GA4 doesn't put the source on session_start in this export, so a session takes the source and
-- medium of its first event that carries one. Funnel steps are flags for whether the session reached each step.
select
    session_key,
    any_value(user_id)                                                            as user_id,
    any_value(ga_session_number)                                                  as session_number,
    min(event_at)                                                                 as session_start_at,
    cast(min(event_at) as date)                                                   as session_date,
    any_value(device_category)                                                    as device_category,
    any_value(country)                                                            as country,
    arg_min(event_source, event_at) filter (where event_source is not null)      as session_source,
    arg_min(event_medium, event_at) filter (where event_medium is not null)      as session_medium,
    arg_min(event_campaign, event_at) filter (where event_campaign is not null)  as session_campaign,
    {{ channel_group("arg_min(event_source, event_at) filter (where event_source is not null)",
                     "arg_min(event_medium, event_at) filter (where event_medium is not null)") }} as channel,
    max(coalesce(session_engaged, 0)) = 1                                         as is_engaged,
    count(*) filter (where event_name = 'page_view')                              as page_views,
    bool_or(event_name = 'view_item')                                             as viewed_item,
    bool_or(event_name = 'add_to_cart')                                           as added_to_cart,
    bool_or(event_name = 'begin_checkout')                                        as began_checkout,
    bool_or(event_name = 'add_shipping_info')                                     as added_shipping,
    bool_or(event_name = 'add_payment_info')                                      as added_payment,
    bool_or(event_name = 'purchase')                                              as purchased
from {{ ref('stg_ga4__events') }}
group by 1
