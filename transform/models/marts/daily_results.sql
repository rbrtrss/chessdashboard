select
    played_at::date as game_date,
    source,
    time_category,
    my_result,
    count(*) as games
from {{ ref('fct_games') }}
group by played_at::date, source, time_category, my_result
