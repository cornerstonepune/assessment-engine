# ux9a-no-guessed-pages: a page's child is never guessed

Nimish, 2026-10-22, on PR #252's question: "yes, stop guessing." Goal: `goals/ux9a-no-guessed-pages.yaml`. W3, N8.

## Verified

- A page with no readable code joins no paper (`sorting.group`); it is read only once a person gives it to a child
  whose own paper is in the file (`sorting.give`, `inbox.give`, `POST /read/run/{id}/page`). On a fresh local copy
  (`bin/testdb fresh`), 2026-10-22: `cd packages/engine && uv run pytest -q tests/test_no_guessed_pages.py` → 5 passed;
  the same five failed on main's code first (5 failed).
- Marking lists such a page by its number, drawn small, a button per child whose paper is in the file (a copy short of
  a page first); one tap keeps the person's word on the file's run and reads it again:
  `cd apps/web && npx playwright test tests/u48-no-guessed-pages.spec.ts tests/u44-upload-on-marking.spec.ts
  tests/u41-what-a-scan-lacks.spec.ts tests/u3-marking.spec.ts` → 10 passed.
- Changed on purpose: four sorting tests said a page with no code joined the copy before it, or a library worksheet's
  copy after it (the 2026-09-23 R5-H14 case). They now say it is nobody's until a person says whose.

## Handoff

- **Live:** nothing until merged and deployed. No migration: the person's word is kept on `flow_run.result.given`.
- **Manual, once deployed:** a class scan with one page's code covered; give it on Marking in one tap.
- **Not done here:** a page can be given only to a child whose own paper (by its code) is in the same file; a copy of a
  library worksheet printed bare is named by a person as before.
