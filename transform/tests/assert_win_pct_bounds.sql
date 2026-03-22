-- Validate that win_pct is between 0 and 100 in opening_stats
select 'opening_stats' as mart, win_pct
from {{ ref('opening_stats') }}
where win_pct < 0 or win_pct > 100
