{{ config(materialized='table') }}

-- monthly_win_rate: Win rate per player, source, year, and month.

with white_games as (
    select
        white_player as player,
        source,
        year,
        month,
        count(*) as games,
        count(*) filter (where result = '1-0') as wins
    from {{ ref('stg_games') }}
    where year is not null and month is not null
    group by white_player, source, year, month
),

black_games as (
    select
        black_player as player,
        source,
        year,
        month,
        count(*) as games,
        count(*) filter (where result = '0-1') as wins
    from {{ ref('stg_games') }}
    where year is not null and month is not null
    group by black_player, source, year, month
),

combined as (
    select player, source, year, month, games, wins from white_games
    union all
    select player, source, year, month, games, wins from black_games
)

select
    player,
    source,
    year,
    month,
    cast(year as varchar) || '-' || lpad(cast(month as varchar), 2, '0') as period,
    sum(games) as games,
    sum(wins) as wins,
    round(sum(wins)::float / nullif(sum(games), 0) * 100, 1) as win_rate
from combined
group by player, source, year, month
order by player, source, year, month
