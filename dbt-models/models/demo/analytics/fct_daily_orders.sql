select
    order_date,
    count(*) as order_count,
    round(sum(order_total_usd), 2) as gross_revenue_usd,
    round(avg(order_total_usd), 2) as average_order_value_usd
from {{ ref('stg_demo_orders') }}
group by 1
