# ux8b-papers-named

Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now for math, making sure that every screen and
every other representation is thought through well: it's clear, it's accurate, clickability is fine." Slice UX8b of the
audit in `docs/notes/ux8-every-screen.md` (#253): its findings 9, 10 and 17.

## Verified

- Measured first: `u45-papers-named.spec.ts`, one test per sentence, run on the code before the change: all five failed
  ("R22-M01" on Marking, the marking page's lane "Addition", "Sat —", no link "What the class did this week", no
  column saying why a child has none)
- After the change, with every test it touches (s3, s5, s7, s8, s11, s12, u2, u33, u38, m2): all passed.
- `bin/engine done ux8b-papers-named` (2026-10-21, on a fresh database): all five of Nimish's sentences PROVED; "every
  page still holds": 291 passed (11.1 min); `bin/check`: 28 passed. NOT DONE only because the work is not on main or
  live yet.

## Handoff

- **Live:** nothing yet; this pull request waits for review.
- **What changed, for an educator:**
  - A paper is named by its skill and level ("2-digit + 2-digit · Medium") on Marking, a read paper, Check the answers,
    the child's papers, the paper's own page and the class's papers to approve. One definition, `paperName` in
    `lib/queries-papers.ts`, in the order the Assessments list already named papers. The printed code stays, as small
    text ("Printed code CS…"), for matching a page in hand.
  - A library worksheet's own page is "2-digit + 2-digit · Medium · sheet 1", its code beneath.
  - A read paper's lanes are the skills every other page names, not the registry's words for the question's skill.
  - A paper with no date no longer says "Sat —".
  - "This week's declaration" is "What the class did this week", the page's title says the same, and its way back is
    "← U38-CLASS · home assessments".
  - Home assessments has a column "Not enough checked work yet", so a class's "0 proposed" says why.
  - "Waiting for a teacher to approve" on a child's papers is "an educator".
- **Tests changed:** s3, s7, s8, s11 and s12 checked the old headings ("Paper CS…", "Worksheet R…") word for word; they
  now check the code beneath the heading, and the sheet's link by its number.
- **Database:** none. No migration, no seed, no bank query (`queries-approve.ts` drops a column no page reads now).
- **Next:** UX8c, one meaning per word.
