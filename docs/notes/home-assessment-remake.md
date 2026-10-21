# home-assessment-remake

Nimish, 2026-10-21: an educator sees a home assessment only once it prints; when it is not good, they could not make
another the same week. "There should not be any lock … remove that constraint ASAP."

## Verified

Filled from this session's runs below; each line names the command that proves it.

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
