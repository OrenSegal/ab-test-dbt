-- One row per player, typed and renamed. No business logic here.
select
    cast(userid as {{ dbt.type_bigint() }})         as user_id,
    cast(version as {{ dbt.type_string() }})        as variant,
    cast(sum_gamerounds as {{ dbt.type_bigint() }}) as game_rounds_14d,
    cast(retention_1 as boolean)                    as retained_d1,
    cast(retention_7 as boolean)                    as retained_d7
from {{ ref('cookie_cats') }}
