---
globs: ["*.py", "**/pipelines/**", "**/api/**", "**/models/**"]
---
# Financial domain guardrails

## Data integrity
- Missing NAV: never silently skip. Log, flag, handle explicitly
- Returns across dates: verify no gaps. Document handling if gaps exist
- Corporate actions change historical prices. Never compare raw prices across action dates
- Row count BEFORE and AFTER every transform. Log both
- NULL in financial calc must produce NULL, not 0 or NaN
- Check for duplicates on natural keys before insert
- Stale data: flag if most recent data is older than expected

## Calculations
- Returns: (new - old) / old. Document alternatives
- Annualize only periods >1 year. Shorter = absolute return
- CAGR: (end/start)^(365.25/days) - 1. Actual day count
- Drawdown: from peak via running maximum, not from start
- AUM: ₹ lakh/crore, never million/billion, 2 decimal places

## API responses
- Always include: data_as_of timestamp, staleness indicator
- Never return partial data without warning flag
- State actual date range, not requested range
