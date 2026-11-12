-- One row per arm: sample size and the metrics the readout compares.
select
    variant,
    count(*)                                                        as players,
    avg(case when retained_d1 then 1.0 else 0.0 end)                as retention_d1,
    avg(case when retained_d7 then 1.0 else 0.0 end)                as retention_d7,
    avg(cast(game_rounds_14d as {{ dbt.type_float() }}))            as mean_game_rounds,
    avg(case when played_zero_rounds then 1.0 else 0.0 end)         as share_zero_rounds,
    avg(case when reached_30_rounds then 1.0 else 0.0 end)          as share_reached_30_rounds,
    max(game_rounds_14d)                                            as max_game_rounds
from {{ ref('fct_player_experiment') }}
group by variant
