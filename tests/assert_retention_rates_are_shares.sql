select * from {{ ref('agg_experiment_arms') }}
where retention_d1 not between 0 and 1 or retention_d7 not between 0 and 1
