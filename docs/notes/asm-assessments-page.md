# asm-assessments-page (W3, gate R1b / S2: the educator's list of assessments)

Nimish, 2026-10-24, on the Assessments page: "there won't be any papers to approve", "two nice blocks side by side", "a very
proper list of the last 5, last 7 assessments", "we should not use these file names", "ability to name the assessment",
"there is no sequence of anything", "nothing hidden from the system", "everything has to have its own set of approvals".
Goal: `goals/asm_assessments_page.yaml` (`bin/engine done asm_assessments_page`). Web, plus one additive migration.

## What changed

- `/papers` is two equal blocks (Make an assessment: the four kinds; Read an assessment: one drop zone, the Drive link, Read it),
  a tab strip (Assessments | Needs checking | Reading status), the shared filter row (class, topic, subject, kind, week,
  status), and one table of assessments, ten to a page, newest week first.
- An assessment is named from its sheet's own code: skill · level (when every copy is at one level) · grade · kind · day made.
  An educator renames it on its row; the name is a new row in `assessment_name` (append-only, migration
  `20261212090000`, RLS on, the website may insert). An uploaded file's own name is shown small under it, "file: …"; a file
  whose printed codes belong to no assessment is a red row "Not matched to an assessment".
- The steps are fixed columns, each a chip: (To approve, home assessments only) · Made · Printed / given · Uploaded · Read ·
  Checked · Signed off. The row's one action is the next thing: Approve, Print, Upload, See reading, Check N answers, Sign off
  N papers, See results. Answers waiting on a person come before papers still to come back.
- A row opens to its children: roll, child, level, the same steps, score, one action, and "Open pages": the child's own
  scanned pages for this assessment, each opening the whole-page view where any answer opens in the checking screen.
- `/papers/approve` with no class redirects to `/papers?status=approve`; with a class and week it is the pack as before
  (reached from a row's Print for a class assessment, via its card). Per-child level changes stay there.
- Pure logic: `apps/web/lib/assessment-steps.ts` (name, steps, action, file matching). Queries:
  `lib/queries-assessment-extras.ts`; `lib/queries-papers.ts` gains `answers`, `unread`, `day`, `levels`, `signId`.

## Verified

Filled in below with the last output of each command.

## Handoff

- gstack was not installed: the permission layer refused the clone ("Untrusted Code Integration"). /design-review, /qa and
  /review did not run; the same checks were done with Playwright (screenshots at 1440 px) and the Superpowers skills.
- The migration needs the rehearsal workflow before merge.
- NAV owns the menu: `u53-the-menu.spec.ts` carries a one-line `MOVED` map for `/papers/approve`; if NAV removes the menu
  item, drop that entry with it.
