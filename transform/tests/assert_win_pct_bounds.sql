-- Validate that win_pct is between 0 and 100 in all aggregate marts
select 'player_stats' as mart, win_pct
from {{ ref('player_stats') }}
where win_pct < 0 or win_pct > 100

union all

select 'opening_stats' as mart, win_pct
from {{ ref('opening_stats') }}
where win_pct < 0 or win_pct > 100

union all

select 'monthly_win_rate' as mart, win_pct
from {{ ref('monthly_win_rate') }}
where win_pct < 0 or win_pct > 100
