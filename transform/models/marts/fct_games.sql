with games as (
    select * from {{ ref('stg_games') }}
),

eco as (
    select * from {{ ref('eco_codes') }}
),

joined as (
    select
        g.game_id,
        g.source,
        g.played_at,
        g.result,
        g.eco,
        coalesce(e.opening_name, 'Unknown') as opening_name,
        coalesce(e.opening_variant, 'Unknown') as opening_variant,
        g.time_category,
        g.my_color,
        g.my_result,
        g.my_rating,
        case
            when g.my_rating - g.opponent_rating < -200 then 'much_stronger'
            when g.my_rating - g.opponent_rating < -50 then 'stronger'
            when g.my_rating - g.opponent_rating <= 50 then 'even'
            when g.my_rating - g.opponent_rating <= 200 then 'weaker'
            else 'much_weaker'
        end as opponent_strength,
        g.moves
    from games g
    left join eco e on g.eco = e.eco
)

select * from joined
