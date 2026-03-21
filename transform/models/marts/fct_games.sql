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
        g.white_username,
        g.black_username,
        g.white_rating,
        g.black_rating,
        g.result,
        g.eco,
        coalesce(e.opening_name, 'Unknown') as opening_name,
        coalesce(e.opening_variant, 'Unknown') as opening_variant,
        g.time_control,
        g.time_category,
        g.my_color,
        g.my_result,
        g.my_rating,
        g.opponent_rating,
        g.moves
    from games g
    left join eco e on g.eco = e.eco
)

select * from joined
