# m1-13: the curriculum screens (W1, gate N1, screens only)

## Verified
- `cd apps/web && npx playwright test tests/m1-13-curriculum-fill.spec.ts --reporter=line` → 7 passed. Written first and seen failing (every address 404 with the pages absent, 5 of 7 red; the switch and the token check passed vacuously).
- Neighbours, same machine: `tests/u51-ux-rules, u53-the-menu, u1-today, u15-menu-and-today, m1-04-k2-voice-notes, u71-results-by-topic, u33-one-count` with the spec → 49 passed.
- `bin/check` → 34 passed. `npx tsc --noEmit` and `npx eslint --max-warnings 0` on the changed files → clean.
- Screenshots at 1280 and 390 px: `docs/screens/m1-13/` (browse, fill, walk, offers, both empty states).
- The walk-through, counted by the spec: open the walk (1 tap), Edit and Save the steps (2), Keep the thinking (1), Send back a level (1) = 5 taps for three drafted parts, then the empty state.

## What a person can do (behind `curriculum.screens_enabled`, config, off)
- `/curriculum/browse`: each K2 section with a bar, a state (icon, word, colour) and a count per part and skills; open a section, search, ten rows a page; a row opens the activity.
- `/curriculum/fill`: per part, how many are the school's, drafted (check me), kept by a person, or empty; the walk-through of drafted parts (`/curriculum/fill/walk`), Keep / Edit / Send back through `POST /curriculum/page/confirm|edit|revert`.
- `/curriculum/fill/[code]`: one activity, every part and who wrote it, the same three answers.
- `/curriculum/offers`: each offered skill with the activity, what is already linked, the reason; Yes / No through `POST /curriculum/offers/answer`.

## Simplest readings taken (for the PR body)
- Branch carries #398 and #399 (merged locally; two small conflicts resolved, one ordering change in `map_ledger.apply`: the single-proposal check first). It diffs smaller once they merge.
- "Staff preview": the switch `curriculum.screens_enabled` stands in until the shared preview helper lands.
- "Drafted (check me)" counts every part with source `drafted`; a checker-doubted one is first in the walk.
- "Send back" is the engine's revert (the part is emptied).
- The activity page link goes to `/curriculum/fill/[code]` until the other builder's activity page exists (`browse/page.tsx`, one link).
- Checkers/marking view skipped: the data is a CSV download (`/api/checkers-sheet`), no route returns rows.
- No new shell: the site's top bar stays (docs/ux-rules.md rule 11); the sidebar and tab bar are the shell builder's.
- Not reused: `DataTable`, `FilterBar`, `StatusChip` carry the older tokens; D-075's palette is the brief.

## Handoff
- Found in #398/#399 by the review, not changed here: a rerun of `engine curriculum propose` re-offers offered and refused skills (`cli_map.py`); `map_ledger.apply` supersedes per page, not per part, and counts rejected rows; the page and offer routes do not refuse while the switch is off (the site does).
- Config rows added: `curriculum.screens_enabled`, `curriculum.fill_green`, `curriculum.fill_amber`. `<html data-scheme="light">` holds the site light, as tokens.css says.
- Undoing a yes is `engine curriculum revert`; there is no screen for it.
