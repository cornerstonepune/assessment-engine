# chk-whose-paper — whose paper is it, and where the Yes button sits

W3, gate 6 (validation and sign-off; I am not certain this is the gate Nimish would name — BUILD-ORDER does not say it in one line).
Goal: `goals/chk_whose_paper.yaml`. Nimish, 23 Oct 2026: a clear mark per child beside each crop, and "that mark ... should be in that same box".

## Verified

Run on a local copy built by `bin/testdb fresh` (Postgres 16, this repository's migrations), never on live.

| Claim | Command | Last output |
|---|---|---|
| The Yes button is in the answer box under "The reader thinks the child wrote N"; nothing above the card but the progress line | `cd apps/web && npx playwright test tests/s44-whose-paper.spec.ts` (test 1) | 5 passed |
| Beside the crop: the page small with the crop outlined, the code read off the page, "Copy 2 of 4 in this file · page 1 of 1" | same (test 2) | passed |
| Checking per child: strip "Esha · paper CSA00005 · answer 1 of 3 · 2 left", the next-child step only on a child's last answer, a list of the file's children | same (test 3) | passed |
| The same photograph on two children's copies: a plain notice, Yes disabled until a person chooses; the choice is a new `page_choice` row | `uv run pytest tests/test_whose_paper.py` and the spec's test 4 | 7 passed; spec passed |
| After sign-off: "Scores recorded for Devi: 2 of 3 right", the child's page, and for the last paper "See its Results"; the Children page shows the score | spec test 5 | passed |
| The goal, the map, every promise, lint | `bin/engine goal chk_whose_paper` | 3/3 criteria met · GOAL ACHIEVED |
| `engine done` | `bin/engine done chk_whose_paper` | every sentence PROVED, every criterion PASSED; NOT DONE only for "not on main yet" and "live database did not answer" |
| 33 + 48 neighbouring browser tests (u1, u13, u14, u16, u38, u43, u45, u49, u50, u51, s1, s4, s42, u9, workflows) | `npx playwright test <those files>` | all passed after `u50`'s heading check was moved to the question over the picture |

Screenshots at 1440 px (before on main, after, the same-photograph notice, scores recorded) were taken in the session and are not in git: the repository ignores `*.png`. `npx playwright test tests/s44-whose-paper.spec.ts` writes the three "after" ones to `apps/web/test-results/whose-paper/`.

Not run here: the whole engine suite and the whole browser suite (CI does). Eight `tests/api` tests that print a PDF through Chromium fail in this container because the pre-installed Chromium is a different build; they do not touch these files.

## Were the scores recorded, and where do they show

Read from the code and shown on the seeded copy; **the live database could not be reached, so I cannot say what Nimish's Grade 1 file holds.**

- Recorded: yes. Each answer's mark (right / wrong / blank) is stored on `item_result` when it is read or corrected. Signing a paper off (`confirm_results`) writes one `evidence_event` per answer, marks the answers `confirmed` and rebuilds `child_skill_state`. The sign-off page's "N of M right" and the assessment card's Score column read the same rows.
- Shown before: the Score column on the Assessments table (hidden below 768 px) and on the assessment card; the paper's own page. **Not shown**: the Children page (it lists learning gaps only) and nothing said "scores recorded" after sign-off. That is the cause of "no score anywhere he looked".
- Fixed: a "Last paper" column on the Children page (the newest signed-off paper's "N of M right"); a line "Scores recorded for <first name>: N of M right" with a link to the child on the sign-off page; and, when no paper of the assessment is left to sign off, a link to its Results.

## Handoff

- Migration `20261205090000_a_person_chooses_on_a_doubtful_page.sql`: one additive table, `page_choice` (append-only, RLS by `apply_conventions`). Needs `rehearse update-live` before it goes live (BUILD-ORDER rule for migrations).
- Engine: `engine/w3_read/whose_paper.py` (in step N9 of the map); routes `GET /capture/{id}/proof`, `POST /paper/page-choice`; `lib/engine-routes.ts` regenerated.
- The guard is shown by the screen, and the Yes button is disabled there. The engine does not yet refuse a Yes posted by hand to `/capture/correct`; if that matters, the refusal belongs in `marking.correct`.
- "Copy N of M": M is the highest copy number among the readings cut from that file; a copy that was skipped (not read) leaves no reading, so M can undercount.
- The list of children in a file is by roll number and paper code, not first name: a name is read through `pii.read_child`, which logs each read, and a list would log one per child per view.
- The code on a page is read live with the engine's QR reader each time a card opens (about a second); nothing is cached.
- Phone layout not worked on (1440 px first, as asked).
