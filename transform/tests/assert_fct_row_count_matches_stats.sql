-- Validate that fct_games row count equals sum of daily_results.games
with fct_count as (
    select count(*) as total_games from {{ ref('fct_games') }}
),

daily_count as (
    select sum(games) as total_games from {{ ref('daily_results') }}
)

select
    f.total_games as fct_total,
    d.total_games as daily_total
from fct_count f
cross join daily_count d
where f.total_games != d.total_games
