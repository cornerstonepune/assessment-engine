# E0: English Grades 3–4 in the system, as drafts

E0 (BUILD-ORDER, 2026-10-22), beside the C slices: it adds no table. Goal: `goals/e0-english-in-the-system.yaml`.
Decision record: ADR 0093. PR #284.

## Verified

On a database built fresh from this branch (`bin/testdb fresh`), the website run as its own role
(`TEST_WEB_DATABASE_URL`, as CI does), 2026-10-22, before the last merge of main (UXF, #279).

- `bin/engine done e0-english-in-the-system`: each of Nimish's 7 sentences `PROVED` (loaded as drafts, loading twice
  moves nothing; nothing English drawn before approval; an approval keeps the name and the date; the maths exactly as it
  was; a kind written later does not take English's links for good; the page; every member of staff may approve).
  Criteria: the English rows `7 passed`, `engine load --check` `unchanged on a second run`, the page `2 passed`,
  `bin/check` `30 passed`. `NOT DONE` only for what is not live: not on main, and the live database did not answer from
  here (`ConnectionTimeout`), so its migrations are unchecked.
- The three checks that read every skill as a maths skill now read the maths on purpose (they found English because the
  school had only maths): `tests/test_rung_folded.py` (7 passed), `tests/test_library.py` (the count of levels a worksheet is
  made from), `tests/test_skill_links.py`, `tests/test_topics.py`, `u31` and `u50` in the browser.
- Two real faults, found by CI and fixed at their cause (ADR 0093, points 7 and 8):
  1. **The site would have opened on English.** Subjects were listed by code, `ENG` before `NUM`, so Today and every page
     opened on English, with nothing approved in it, for anyone who had not chosen. Now a subject with approved skills comes
     first (`lib/choices.ts`). **Nimish decides** which subject the site opens on, if not this.
  2. **The website could not record an approval of a kind**: `permission denied for table question_type_approval` as the
     website's role (it passes as the table's owner, which is how it was first run). One grant, in
     `20261203090000_the_website_may_add_an_approval_of_a_kind.sql`.
- After B4 (rung folded in), English skills are loaded with their grade and description in the skill's own row; no `rung` row.
- The skill page no longer breaks the `purpose` UX rule (UXF), so it is off `ux.frozen` in `workflows.json`.

## Screens

Before (Maths only, a copy with the English rows taken out) and after (English as a subject row, a draft skill, "waiting
for approval", and the skill's page with Approve on each level and each kind), saved by the session, not in git:
the Curriculum page lists each English skill with what each level asks; its page shows each level and how it is asked,
says "a person checks every answer" for a written answer, lists the mistakes it watches for, and offers Approve to any
member of staff, saved with their name and the date.

## What waits (not faked)

- A sample's question, right answer and wrong answers, each naming a mistake: no table holds them. Nimish decides which slice.
- Send back with a reason: C5. The three observed kinds and the 56 observed skills: C2.
- **Rehearsal on a copy of live** (`rehearse update-live`, a manual workflow that reads live): not run when this note was
  written; it must pass before the PR is called ready.

## Handoff

- Live: nothing. Draft PR #284, not merged.
- Merge order: #285 (B4b) renames `skill_set` to `skill`. This branch names `skill_set` in its queries, loader and tests, so
  whichever merges second renames those too; the one new migration (a grant on `question_type_approval`) is unaffected.
  Its timestamp (20261203…) must sort after the newest on main (`test_migration_order`).
- Next: the rehearsal, then Nimish merges. After the merge, `bin/update-live` loads English as drafts on live.
