-- accepted_values(code) is a superset
select id, code from {{ ref('raw_regions') }}
