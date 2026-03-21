-- Validate that wins + losses + draws = games_played in player_stats
select
    source,
    my_color,
    time_category,
    games_played,
    wins + losses + draws as computed_total
from {{ ref('player_stats') }}
where wins + losses + draws != games_played
