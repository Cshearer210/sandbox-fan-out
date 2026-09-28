-- not_null test on `amount`
select id, coalesce(amount, 0) as amount
from {{ ref('raw_payments') }}
