-- Validate that sum of monthly_win_rate.games_played equals fct_games row count
with monthly_count as (
    select sum(games_played) as total_games from {{ ref('monthly_win_rate') }}
),

fct_count as (
    select count(*) as total_games from {{ ref('fct_games') }}
)

select
    m.total_games as monthly_total,
    f.total_games as fct_total
from monthly_count m
cross join fct_count f
where m.total_games != f.total_games
