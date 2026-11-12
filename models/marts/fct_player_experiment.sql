-- Player-level fact table the experiment analysis reads from.
select * from {{ ref('int_player_outcomes') }}
