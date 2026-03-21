select
    source,
    my_color,
    time_category,
    count(*) as games_played,
    sum(case when my_result = 'win' then 1 else 0 end) as wins,
    sum(case when my_result = 'loss' then 1 else 0 end) as losses,
    sum(case when my_result = 'draw' then 1 else 0 end) as draws,
    round(100.0 * sum(case when my_result = 'win' then 1 else 0 end) / count(*), 1) as win_pct,
    min(played_at) as first_game,
    max(played_at) as last_game
from {{ ref('fct_games') }}
group by source, my_color, time_category
