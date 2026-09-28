-- unique test on `user_id`
select distinct user_id
from {{ ref('raw_events') }}
