select * from {{ ref('stg_cookie_cats') }} where game_rounds_14d < 0
