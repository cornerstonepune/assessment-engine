# M1-12l: Opus only

## Verified
- Runs 28 and 29 (60 dev pages, both checkers): Opus disagreed on 9 of 55, Sonnet on 5; Sonnet found every fault Opus found on 46 pages and missed one on 9.
  Cost per page measured from the run-28 log: Opus 0.0060, Sonnet 0.0036.
- Decision (orchestrator, 6 Nov): Opus keeps checking; `k2.checkers.shadow` is `[]` (saves 0.0036 a page, about 13%).

## Handoff
- `load_settings` after merge. To compare again, name `k2_page_check_b` in the row.
