select
    eco,
    opening_name,
    opening_variant,
    time_category,
    count(*) as games_played,
    sum(case when my_result = 'win' then 1 else 0 end) as wins,
    sum(case when my_result = 'loss' then 1 else 0 end) as losses,
    sum(case when my_result = 'draw' then 1 else 0 end) as draws,
    round(100.0 * sum(case when my_result = 'win' then 1 else 0 end) / count(*), 1) as win_pct,
    round(avg(my_rating), 0) as avg_my_rating,
    round(avg(opponent_rating), 0) as avg_opponent_rating
from {{ ref('fct_games') }}
group by eco, opening_name, opening_variant, time_category
