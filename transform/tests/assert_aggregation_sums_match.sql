-- Validate that win + loss + draw game counts equal total games in daily_results
with totals as (
    select
        game_date,
        source,
        time_category,
        sum(games) as total_games
    from {{ ref('daily_results') }}
    group by game_date, source, time_category
),

by_result as (
    select
        game_date,
        source,
        time_category,
        sum(case when my_result = 'win' then games else 0 end)
        + sum(case when my_result = 'loss' then games else 0 end)
        + sum(case when my_result = 'draw' then games else 0 end) as computed_total
    from {{ ref('daily_results') }}
    group by game_date, source, time_category
)

select
    t.game_date,
    t.source,
    t.time_category,
    t.total_games,
    b.computed_total
from totals t
join by_result b
    on t.game_date = b.game_date
    and t.source = b.source
    and t.time_category = b.time_category
where t.total_games != b.computed_total
