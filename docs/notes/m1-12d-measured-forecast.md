# m1-12d: the forecast reads what the calls cost (W1, gate N1)

## Verified
- tests/test_k2_forecast.py and test_k2_draft.py pass on a local copy. No call made.

## What changed
- `forecast` (the `forecast` run choice, free) takes the mean cost of an answered call of the prompt row it will ask (version-matched, status ok, last 200) once at least `measured_min_calls` (5) have been paid for; else the assumed tokens. The share of pages a checker sent back is read from the ledger's history (a second round) once `measured_min_pages` (20) pages are drafted. It names which of these were measured and over how many; with nothing measured it says "token counts assumed, not measured", as before.
- Limit: a call's cost is a batch of `batch_pages` pages, so a forecast for a page count that is not a multiple of it is rounded up to whole calls; the worst case still assumes every page is asked again in every round and revised.

## Handoff
- Dispatch `forecast` after the dev run for the first measured forecast of the draft stage.
