-- Adds the user-level flags the analysis needs on top of the staged row.
select
    user_id,
    variant,
    variant = 'gate_40'                         as is_treatment,
    game_rounds_14d,
    game_rounds_14d = 0                         as played_zero_rounds,
    -- Players below level 30 never reach either gate, so both arms saw the same game.
    game_rounds_14d >= 30                       as reached_30_rounds,
    retained_d1,
    retained_d7
from {{ ref('stg_cookie_cats') }}
