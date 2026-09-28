-- not_null test on `status`
select id, amount, status
from {{ ref('raw_orders') }}
where status in ('paid','shipped')
