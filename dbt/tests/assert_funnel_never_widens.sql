-- The funnel counts sessions that reached each step, so at the session level a step can't hold more than the session
-- total. Steps can be skipped (a purchase without add_payment_info is possible in GA4), so only the first step is
-- the hard ceiling; this returns any segment where a step exceeds its session count.
select cut, segment, step, sessions
from {{ ref('rpt_funnel') }}
where share_of_sessions > 1
