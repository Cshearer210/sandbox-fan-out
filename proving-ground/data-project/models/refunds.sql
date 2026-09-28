-- not_null(amount) severity: warn
select id, amount from {{ ref('raw_refunds') }}
