{{ config(materialized='table') }}

-- time_control_breakdown: Game counts per player, source, and time control.

with white_games as (
    select
        white_player as player,
        source,
        time_control,
        count(*) as games
    from {{ ref('stg_games') }}
    where time_control is not null
    group by white_player, source, time_control
),

black_games as (
    select
        black_player as player,
        source,
        time_control,
        count(*) as games
    from {{ ref('stg_games') }}
    where time_control is not null
    group by black_player, source, time_control
),

combined as (
    select player, source, time_control, games from white_games
    union all
    select player, source, time_control, games from black_games
)

select
    player,
    source,
    time_control,
    sum(games) as games
from combined
group by player, source, time_control
order by player, source, games desc
