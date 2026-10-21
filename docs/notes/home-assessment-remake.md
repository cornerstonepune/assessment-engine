# home-assessment-remake

Nimish, 2026-10-21: an educator sees a home assessment only once it prints; when it is not good, they could not make
another the same week. "There should not be any lock … remove that constraint ASAP."

## Verified

- The four new engine tests fail on main, on the lock itself ("already has this week's home assessment"), and pass here.
  `cd packages/engine && uv run pytest -q tests/test_focus_paper.py tests/test_maker.py tests/test_read_back.py`
  On main: 4 failed, 37 passed. On this branch: 41 passed (2026-10-21).
- The whole engine suite. `cd packages/engine && uv run pytest -q`: 2586 passed, 2 skipped, in 37 min on a cloud
  container. Inside `bin/engine done` that is past its 30-minute limit there, so the criterion reads "timed out". CI's
  engine job ran the same suite green on e9b6f91 in 21 min.
- The pages. `cd apps/web && npx playwright test tests/s11-focus-paper.spec.ts tests/m4-the-maker.spec.ts
  tests/u16-assessments.spec.ts tests/u9-papers.spec.ts tests/u37-papers-grouped.spec.ts tests/u38-make-and-marking.spec.ts
  tests/u1-today.spec.ts tests/m2-make-papers.spec.ts tests/u33-one-count.spec.ts tests/u2-children.spec.ts
  tests/s7-paper-from-library.spec.ts`: 52 passed. CI browser job green on e9b6f91.
- `bin/check`: 28 passed.
- `bin/engine done home-assessment-remake`: all five of Nimish's sentences PROVED; the whole-suite criterion timed out
  on the container, as above.

## Handoff

- **Live:** nothing yet; the pull request waits for review and merge.
- **What changed:** the engine no longer refuses a second home assessment in a week (`focus_paper.make`,
  `maker._plan`). `focus_paper.approved` returns the newest, with the earlier ones as `replaced`. A click names the paper
  it saw (`replaces`); once a colleague's newer one exists, the click is refused rather than printing two.
  The child's page offers "Make a new home assessment" and names the earlier ones as replaced in one line. Papers gives an
  unread earlier one the stage "replaced by a newer one". The earlier paper's own page names the paper that replaced it.
- **Database:** no migration. No home paper writes a prescription row, so `prescription_one_per_child_week_kind`
  never touched it. A paper's `created_at` is now the click's own moment (`clock_timestamp()`), so "newest" is exact
  even inside one transaction.
- **Two clicks:** on the child's page and a class's home assessments, the "which paper did you see" check. In the class
  maker (`/papers/make`), its own `once` token already makes one form print once, however often it is sent.
