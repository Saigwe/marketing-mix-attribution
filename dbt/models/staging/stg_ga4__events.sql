-- One row per GA4 event, with a session key (GA4 session ids are unique only within a user).
select
    user_pseudo_id || '-' || ga_session_id                      as session_key,
    user_pseudo_id                                              as user_id,
    ga_session_id,
    ga_session_number,
    event_name,
    event_at,
    event_date,
    device_category,
    country,
    event_source,
    event_medium,
    event_campaign,
    engagement_time_msec,
    session_engaged,
    nullif(nullif(transaction_id, '(not set)'), 'NaN')          as transaction_id,
    revenue_usd
from {{ source('bronze', 'ga4_events') }}
