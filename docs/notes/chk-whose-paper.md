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

CI found two mistakes of mine, both fixed: `rules.json` lacked the six rules of the new `page_choice` table (shard 10), and the Children page's "Last paper" query gave every child "0 of 0 right" because an aggregate over no rows still returns a row (browser: u35, u50-declutter, u8). The spec now checks that an unsigned child has no score.

## Were the scores recorded, and where do they show

Read from the code and shown on the seeded copy; **the live database could not be reached, so I cannot say what Nimish's Grade 1 file holds.**

- Recorded: yes. Each answer's mark (right / wrong / blank) is stored on `item_result` when it is read or corrected. Signing a paper off (`confirm_results`) writes one `evidence_event` per answer, marks the answers `confirmed` and rebuilds `child_skill_state`. The sign-off page's "N of M right" and the assessment card's Score column read the same rows.
- Shown before: the Score column on the Assessments table (hidden below 768 px) and on the assessment card; the paper's own page. **Not shown**: the Children page (it lists learning gaps only) and nothing said "scores recorded" after sign-off. That is the cause of "no score anywhere he looked".
- Fixed: a "Last paper" column on the Children page (the newest signed-off paper's "N of M right"); a line "Scores recorded for <first name>: N of M right" with a link to the child on the sign-off page; and, when no paper of the assessment is left to sign off, a link to its Results.

## Merge of main (#315 page 2 is never page 1 again, #316 each answer once), 2026-10-23

Conflicts: `engine-routes.ts` (generated; regenerated with `bin/engine contract`, both `/pages` and `/proof` are in) and `api/routes/capture.py` (one import line, both modules kept). Everything else merged by git.
One function, not two: #315's `same_page.fingerprint` already says "this is the same photograph", so `whose_paper` uses it and its own `page_hash` is gone. The two guards stay two questions: #315 asks whether a page of a copy repeats an earlier page of the same copy; this one asks whether a page repeats a page of another child's copy.

| Claim | Command | Last output |
|---|---|---|
| Engine, files touched and neighbours | `cd packages/engine && pytest -q tests/test_whose_paper.py tests/test_same_page.py tests/test_layout.py tests/test_no_guessed_pages.py tests/test_photograph_page.py tests/test_spine_page.py tests/test_promises.py` | 66 passed |
| The map, promises, lint | `bin/check` | 30 passed |
| Types | `cd apps/web && npx tsc --noEmit` | no errors |
| Browser: this goal with #315/#316's | `npx playwright test tests/s44 u52 u61 u50 u51 u9 u45 u37 u35 u8` | 41 passed |

## Handoff

- Migration `20261205090000_a_person_chooses_on_a_doubtful_page.sql`: one additive table, `page_choice` (append-only, RLS by `apply_conventions`). Needs `rehearse update-live` before it goes live (BUILD-ORDER rule for migrations).
- Engine: `engine/w3_read/whose_paper.py` (in step N9 of the map); routes `GET /capture/{id}/proof`, `POST /paper/page-choice`; `lib/engine-routes.ts` regenerated.
- The guard is shown by the screen, and the Yes button is disabled there. The engine does not yet refuse a Yes posted by hand to `/capture/correct`; if that matters, the refusal belongs in `marking.correct`.
- "Copy N of M": M is the highest copy number among the readings cut from that file; a copy that was skipped (not read) leaves no reading, so M can undercount.
- The list of children in a file is by roll number and paper code, not first name: a name is read through `pii.read_child`, which logs each read, and a list would log one per child per view.
- The code on a page is read live with the engine's QR reader each time a card opens (about a second); nothing is cached.
- Phone layout not worked on (1440 px first, as asked).
