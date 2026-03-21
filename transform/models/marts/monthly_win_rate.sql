select
    date_trunc('month', played_at) as month,
    source,
    time_category,
    my_color,
    count(*) as games_played,
    sum(case when my_result = 'win' then 1 else 0 end) as wins,
    sum(case when my_result = 'loss' then 1 else 0 end) as losses,
    sum(case when my_result = 'draw' then 1 else 0 end) as draws,
    round(100.0 * sum(case when my_result = 'win' then 1 else 0 end) / count(*), 1) as win_pct,
    round(avg(my_rating), 0) as avg_rating
from {{ ref('fct_games') }}
group by date_trunc('month', played_at), source, time_category, my_color
