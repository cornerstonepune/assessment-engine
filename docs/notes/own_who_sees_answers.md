# own_who_sees_answers: each educator sees their own answers and papers; curriculum stays open

Nimish, 27 Oct 2026 (his words are in `goals/own_who_sees_answers.yaml`). Goal: `bin/engine done own_who_sees_answers`.
W3 (the educator's site over W2/W3's data); no gate moved. One migration: `20261222090000_who_sees_a_paper.sql`.

## The rule, in one place

`staff_sees(role, classes, subjects, staff_id, section, subject, uploaded_by)` in the migration. A coordinator sees
everything. An educator sees what they put in themselves, or what is of a class on their staff entry, in a subject on it
(no subject named on the entry, or none known for the paper, is every subject). `staff_sees_sheet`, `staff_sees_capture`
ask it of one printed copy or one scan. The website hands it the signed-in person (`apps/web/lib/reach.ts`) and holds no
rule of its own; changing who sees what is one `create or replace function` in a new migration.

Not narrowed, on purpose: Curriculum, a skill's page, Skills to approve, the question bank, the worksheet library, the
reader's accuracy panel ("How the reader is doing", a measure of the reader across the school, no child in it), and the
decisions themselves (approving a skill stays every educator's, goals/ux9c-one-role.yaml).

## Where it applies

| Place | What it reads | Now |
|---|---|---|
| Check answers list and its count (`checkQueue`) | answers waiting | the papers the person sees |
| Check answers card (`?id=`) | one answer | refused in words when not theirs |
| Menu count, What needs doing (`tasksFor`) | answers, sign-offs, scans with nothing read, class work | the same rule; class work by `reachOf` |
| Assessments list, By topic, class filter, the card, file links | papers | `narrowed(f, me)`: the papers the person sees |
| Assessments card page | one assessment's copies | the copies seen; refused in words when none and not their class |
| Upload papers: papers, file list (`lastScans`) | papers, files read | papers seen; a file seen by its uploader or by whoever sees a paper in it, counted by the copies seen |
| A paper's page (`/capture/[id]`), printed paper (`/worksheets/CS…`), its images and print pack | one paper | refused in words / 403 |
| Sign-off (`confirmPaper`), check, judge, correct, name a mistake, change a key, page choice | one paper or answer | `mustSee`: refused in words, nothing written; the child signed for must be the paper's own |
| Give a page, read again | a file's run | the uploader, or whoever sees a paper in it |
| "Given on", "away" on the card | papers by code | only papers the person sees |
| A child's page: answers waiting, papers, sheets; sign off all | a child's papers | class rule for the page; its papers and the sign-off narrowed by the rule (subject too) |
| Class results, children, reports, home assessments, papers to make, class packs | classes | `workScope`: own classes the rule allows; an educator linked to no class sees none |
| Across classes | papers, children | narrowed by the rule |
| Search | children, papers, assessments | narrowed before any name is read |

## Chosen by default (nobody was asked)

- **Staff ids.** The staff list is a config row with no id, so each entry gets one (`id`, a uuid), filled by a trigger on
  whichever door adds a person and kept when the list is rewritten. `capture.uploaded_by` and `flow_run.uploaded_by` hold it.
- **Uploader.** Set by the engine on every new upload from the signed-in email (`staff_id`), on the run and on every paper read
  from it. "Read again" keeps the first uploader (never the person who pressed it). Older uploads have none: the class rule alone.
- **Subjects narrow the class arm only.** What an educator put in themselves is theirs whatever its subject.
- **An educator linked to no class** sees no class's children or papers, only what they put in. Before, they saw every class.
- **A coordinator sees everything**, including with classes on their entry. If Achal's staff row says `coordinator`, he sees
  everything; for "Achal should only see the papers he has uploaded" his row must say `educator`.

## Verified

(filled in at the end of the session, below)

## Handoff

- Needs the rehearsal (`rehearse-update-live.yml`) on the branch before merge: one migration.
- Ask Nimish to confirm the rule (class OR uploader, subject narrows the class arm); it is one function to change.
