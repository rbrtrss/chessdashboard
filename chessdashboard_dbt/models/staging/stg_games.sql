{{ config(materialized='incremental', unique_key='game_id') }}

-- stg_games: Denormalized view of the star schema.
-- Joins fact_games with all dimension tables so downstream
-- models can just SELECT from this single clean table.

select
    g.game_id,
    g.eco,
    g.moves,
    g.time_control,
    g.url,

    -- date fields
    d.date,
    d.year,
    d.month,
    d.day,

    -- event fields
    e.name as event_name,
    e.site as event_site,
    e.round as event_round,

    -- player fields
    pw.username as white_player,
    pb.username as black_player,

    -- result
    r.result,
    case
        when r.result = '1-0' then pw.username
        when r.result = '0-1' then pb.username
        else 'Draw'
    end as winner,

    -- source
    s.source,

    -- opening
    o.name as opening_name,
    o.variation as opening_variation,

    -- derived
    length(g.moves) - length(replace(g.moves, ' ', '')) + 1 as move_count

from {{ source('chessdashboard', 'fact_games') }} g
left join {{ source('chessdashboard', 'dim_date') }} d on g.date_id = d.date_id
left join {{ source('chessdashboard', 'dim_event') }} e on g.event_id = e.event_id
left join {{ source('chessdashboard', 'dim_player') }} pw on g.playing_white_id = pw.player_id
left join {{ source('chessdashboard', 'dim_player') }} pb on g.playing_black_id = pb.player_id
left join {{ source('chessdashboard', 'dim_result') }} r on g.result_id = r.result_id
left join {{ source('chessdashboard', 'dim_source') }} s on g.source_id = s.source_id
left join {{ source('chessdashboard', 'dim_opening') }} o on g.eco = o.eco

{% if is_incremental() %}
  where g.game_id > (select max(game_id) from {{ this }})
{% endif %}
