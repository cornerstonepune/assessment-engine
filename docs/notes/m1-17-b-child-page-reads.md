# M1-17 brick B — the child page read gains growth and ready-next

W3, gate N10 (reading side). Stacked on brick A (#403: `k2_growth.py`); until A merges this PR shows A's files too.
No migration, no model call. Design: `docs/notes/m1-17-design.md` (#402).

## What changed
- `POST /k2/child` (`k2_picture_reads.child_page`) keeps `class`, `roll_no`, `skills` as they were and adds:
  - `growth`: per skill `{skill:{code,name}, first_seen, last_seen, by_month:[{month, level, days}], trend}`. From named,
    individual, confirmed, current (not superseded) observations only; "the rest did as expected" and "not willing" add nothing.
  - `ready_next`: per skill `{skill, because:[{before, strength}]}` from `skill_link_confirmed` only; only `secure` is done.
- Config row `k2.child_page` (`supabase/seed/config.json`, loaded by `engine load --settings`, no migration):
  `growth_min_months` 2, `done_states` ["secure"]. No default in code (a repo test forbids naming a state there): a missing row stops the page with a message naming the fix.
- Queries per page: skill names now ride the cells query (and the class picture's too), the config rides the class query;
  growth and links are one query each. Net +1 over before, still a fixed number whatever the class size.

## Decisions made without an answer
- `tests/test_k2_picture_reads.py` budgets the child page with a sentence at 8 queries; it is now 9 (was 8; +growth, +links,
  -names). The test beside it, that the count is the same for a class of 2 skills or 20, is unchanged and passes. Veto this
  if the 8 was meant as a ceiling on the page.
- `seen_nothing_yet` (design note section 5) is not built: it needs the grade's full skill list and nothing yet asks for it.
- `engine-routes.ts` types only requests, so `bin/engine contract` has nothing to regenerate.

## Verified (local database built by `bin/testdb fresh`; never live)
- `tests/test_k2_child_growth.py` (9) failed first (`growth`, `ready_next` absent), then passed.
- `pytest -q tests/test_k2_picture_reads.py tests/test_k2_reads.py tests/api tests/test_layout.py tests/test_k2_growth.py tests/test_k2_child_growth.py tests/test_loaders.py tests/test_settings.py tests/test_voice_switch.py` → 205 passed.
- `bin/engine load --check` → unchanged on a second run. `bin/check` → 34 passed (it first caught a type error in this
  change, `growth()` may return None; fixed). ruff check and format clean.
- Not run: the whole suite in shards, the browser tests (CI).

## Handoff
Next: the child page and class picture screens, behind the staff preview (the 4b helper), switches off.
