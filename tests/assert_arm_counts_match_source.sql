-- Fails if the arm summary loses or duplicates players compared with the raw seed.
select 1
from (select sum(players) as n from {{ ref('agg_experiment_arms') }}) a
cross join (select count(*) as n from {{ ref('cookie_cats') }}) s
where a.n != s.n
