-- Every attribution model must hand out each order exactly once: attributed orders and revenue equal the orders and
-- revenue of all purchases (every order has at least its own purchasing session in its path).
with totals as (
    select count(*) as orders, sum(revenue_usd) as revenue from {{ ref('fct_orders') }}
)

select a.model, sum(a.attributed_orders) as orders, sum(a.attributed_revenue_usd) as revenue, t.orders, t.revenue
from {{ ref('rpt_attribution_rules') }} a
cross join totals t
group by a.model, t.orders, t.revenue
having abs(sum(a.attributed_orders) - t.orders) > 0.01 or abs(sum(a.attributed_revenue_usd) - t.revenue) > 1
