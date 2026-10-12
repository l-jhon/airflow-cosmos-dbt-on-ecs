select
    cast(order_id as bigint) as order_id,
    cast(order_date as date) as order_date,
    customer_id,
    lower(order_status) as order_status,
    cast(order_total_usd as double) as order_total_usd
from {{ ref('demo_raw_orders') }}
where lower(order_status) != 'cancelled'
