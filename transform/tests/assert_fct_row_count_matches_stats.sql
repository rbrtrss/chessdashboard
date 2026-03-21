-- Validate that fct_games row count equals sum of player_stats.games_played
with fct_count as (
    select count(*) as total_games from {{ ref('fct_games') }}
),

stats_count as (
    select sum(games_played) as total_games from {{ ref('player_stats') }}
)

select
    f.total_games as fct_total,
    s.total_games as stats_total
from fct_count f
cross join stats_count s
where f.total_games != s.total_games
