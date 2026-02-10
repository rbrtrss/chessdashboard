-- player_stats: Aggregated win/loss/draw statistics per player and source.

with white_games as (
    select
        white_player as player,
        source,
        count(*) as games_as_white,
        count(*) filter (where result = '1-0') as wins_as_white,
        count(*) filter (where result = '0-1') as losses_as_white,
        count(*) filter (where result = '1/2-1/2') as draws_as_white
    from {{ ref('stg_games') }}
    group by white_player, source
),

black_games as (
    select
        black_player as player,
        source,
        count(*) as games_as_black,
        count(*) filter (where result = '0-1') as wins_as_black,
        count(*) filter (where result = '1-0') as losses_as_black,
        count(*) filter (where result = '1/2-1/2') as draws_as_black
    from {{ ref('stg_games') }}
    group by black_player, source
)

select
    coalesce(w.player, b.player) as player,
    coalesce(w.source, b.source) as source,
    coalesce(w.games_as_white, 0) as games_as_white,
    coalesce(b.games_as_black, 0) as games_as_black,
    coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0) as total_games,
    coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0) as total_wins,
    coalesce(w.losses_as_white, 0) + coalesce(b.losses_as_black, 0) as total_losses,
    coalesce(w.draws_as_white, 0) + coalesce(b.draws_as_black, 0) as total_draws,
    round(
        (coalesce(w.wins_as_white, 0) + coalesce(b.wins_as_black, 0))::float
        / nullif(coalesce(w.games_as_white, 0) + coalesce(b.games_as_black, 0), 0)
        * 100, 1
    ) as win_rate
from white_games w
full outer join black_games b on w.player = b.player and w.source = b.source
order by total_games desc
