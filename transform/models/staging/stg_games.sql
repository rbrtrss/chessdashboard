with source as (
    select * from {{ source('raw', 'games') }}
),

parsed as (
    select
        game_id,
        source,
        to_timestamp(played_at) as played_at,
        white_username,
        black_username,
        white_rating,
        black_rating,
        result,
        eco,
        time_control,
        moves,

        -- Parse base seconds from time_control
        case
            -- Lichess milliseconds: source is lichess, numeric, >= 10000
            when source = 'lichess'
                and regexp_matches(time_control, '^\d+$')
                and cast(time_control as bigint) >= 10000
                then cast(time_control as bigint) / 1000
            -- Chess.com base+increment format (e.g. "180+2")
            when regexp_matches(time_control, '^\d+\+\d+$')
                then cast(split_part(time_control, '+', 1) as int)
            -- Plain seconds (numeric, < 10000 or non-lichess)
            when regexp_matches(time_control, '^\d+$')
                then cast(time_control as int)
            -- Lichess speed strings
            when lower(time_control) = 'bullet' then 60
            when lower(time_control) = 'blitz' then 300
            when lower(time_control) = 'rapid' then 600
            when lower(time_control) = 'classical' then 1800
            when lower(time_control) = 'ultrabullet' then 30
            -- Chess.com daily/correspondence: fraction format (e.g. "1/259200")
            when regexp_matches(time_control, '^\d+/\d+$')
                then 1800
            else 0
        end as base_seconds,

        -- Parse increment
        case
            when regexp_matches(time_control, '^\d+\+\d+$')
                then cast(split_part(time_control, '+', 2) as int)
            else 0
        end as increment_seconds,

        -- Determine my_color
        case
            when source = 'lichess'
                and lower(white_username) = lower('{{ var('lichess_username') }}')
                then 'white'
            when source = 'lichess'
                and lower(black_username) = lower('{{ var('lichess_username') }}')
                then 'black'
            when source = 'chesscom'
                and lower(white_username) = lower('{{ var('chesscom_username') }}')
                then 'white'
            when source = 'chesscom'
                and lower(black_username) = lower('{{ var('chesscom_username') }}')
                then 'black'
            else 'unknown'
        end as my_color

    from source
),

enriched as (
    select
        game_id,
        source,
        played_at,
        white_username,
        black_username,
        white_rating,
        black_rating,
        result,
        eco,
        time_control,
        moves,
        my_color,

        -- Time category: base + 40 * increment
        case
            when base_seconds + 40 * increment_seconds < 180 then 'bullet'
            when base_seconds + 40 * increment_seconds < 600 then 'blitz'
            when base_seconds + 40 * increment_seconds < 1800 then 'rapid'
            else 'classical'
        end as time_category,

        -- My result
        case
            when result = my_color then 'win'
            when result = 'draw' then 'draw'
            else 'loss'
        end as my_result,

        -- My rating / opponent rating
        case when my_color = 'white' then white_rating else black_rating end as my_rating,
        case when my_color = 'white' then black_rating else white_rating end as opponent_rating

    from parsed
)

select * from enriched
where my_color != 'unknown'
