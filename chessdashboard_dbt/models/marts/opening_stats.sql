{{ config(materialized='table') }}

-- opening_stats: Performance statistics grouped by ECO opening code and source.

select
    eco,
    opening_name,
    source,
    count(*) as total_games,
    count(*) filter (where result = '1-0') as white_wins,
    count(*) filter (where result = '0-1') as black_wins,
    count(*) filter (where result = '1/2-1/2') as draws,
    round(count(*) filter (where result = '1-0')::float / count(*) * 100, 1) as white_win_pct,
    round(count(*) filter (where result = '0-1')::float / count(*) * 100, 1) as black_win_pct,
    round(avg(move_count), 1) as avg_moves
from {{ ref('stg_games') }}
where eco is not null
group by eco, opening_name, source
order by total_games desc
