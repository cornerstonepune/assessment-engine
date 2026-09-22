# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which step we are on and what "done" means. Then `STATE.md` for what
is verified. This file only says where the last session stopped.

## 2026-09-22 — where this session stopped

**Step 7 is live** (PR #11 merged, `10e51cc`). **Step 8 is built on branch `step-8`**: 8a–8d (ADR 0023, 0030 — a
question's skills read from the question, a wrong answer charged to the skill whose step broke, evidence per
skill) and, widened the same day to the team's *Addition & Subtraction Assessment Skill Taxonomy*, 8e–8i (ADR
0031 — 269 cases as rows, levels that hold named cases, 8 new kinds of question, 4 new skills, the bank refilled).
Rehearsed end to end on a fresh copy of live: `engine bank taxonomy` "269 cases · 269 covered · 0 missing · 0
thin", `engine library check` "0 problems", a second refill and a second build change nothing (STATE, 8i).

**Live since 13:56 IST** (PRs #13 and #14; numbers in STATE, 8i). The engine was down 13:16–13:56 after #13 — the
story templates were outside the image; fixed in #14. `go-live.sh` could not upload from this Mac (its network
corrupted every transfer above 16 KB); the server fetched the commit from GitHub and was proved identical to it.
Rerun `deploy/go-live.sh` once the network is sound, so the server again comes from the script. **Not yet proved:
a signed-in click-through on the live link.**

**The reader learns — live since 20:10 IST** (ADR 0032, PR #19). Queue 382 → 624: 570 one click, 53 typing; audit 0
(STATE). Nimish checks child by child; **after each batch run `bin/engine read profile` then `bin/engine read
report`** — the report is the answer to "how many rounds": a kind leaves the queue for good once it reaches 95% of
the last 50 checks. New papers read through `legacy import` pick up the notebooks and the second reader on their
own. **Owed:** `deploy/go-live.sh` (server on `450467b`; nothing it serves changed). **Next reader fix:** 6 of the 9
silent errors left in the replay sit on one paper at 95%+ — most likely the working picked as the answer; confirm on
the crops. **Then, per Nimish's standing direction (BUILD-ORDER):** how skills are read from evidence and the graph
keeps itself honest; the graph readable at a glance.

**Built tonight (PR #22, ADR 0033):** the engine laid out as its workflows and held to `workflows.json`; the How it
works page; `engine promises`, `engine done <goal>`, `bin/check` run by the git pre-commit hook and a Claude Code
Stop hook. **Report work done only with `engine done <goal>` pasted (CLAUDE.md rule 14).**

**Step 12 — the next paper per skill set, live** (ADR 0034, branch `next-paper-per-skill`; migration applied to
live, `engine load`, `engine legacy place` run on live — numbers in STATE). Dhanvi's subtraction mistakes now
aim her SUB.3D.ZERO paper, not ADD.3D.REG. **Owed:** the PR merged (then `engine done next-paper-per-skill`
reads DONE); 12 old questions no skill set holds wait on the pedagogy question below.

**Next, in this order (BUILD-ORDER "Now, in this order", agreed by Nimish tonight):** step 13
`goals/two-child-loop.yaml` — Agastya's and Dhanvi's graphs per skill set, read in plain sentences, drawn for a
teacher, and the next paper's plan from them; build `engine/w3_read/skill_graph.py` against
`tests/test_skill_graph.py` (xfail strict — take each marker off as it passes). Then step 14
`goals/custom-paper.yaml` — `engine/w2_print/compose.py` against `tests/test_compose.py`; it replaces step 10.
Add each new file to `workflows.json` before writing it. **Asked, no answer yet:** N4 (the teacher's Wednesday
declaration) and N7 (the teacher approves the pack) are in no step.

**Open from before, unchanged:** validation (step 6 closes when nothing waits and `engine gold check` has every
finding in the graph); the reader and the teacher's red pen (ADR 0020, no answer yet); PR #12 (`reader-trust`,
ADR 0029) open in the worktree `assessment-engine-reader`.

## Queued reader fixes — found on crops, held while coverage is held

- `G4-SEPW1` q7: two labelled answer boxes wider than `ocr.box_max_width` are thrown away as working area.
- `G3-SEPW1-A` q5: nine answers in nine small printed boxes, one found.
- `G4-SEPW1` q3: the child's digits sit inside the printed line ("4[6] + [5]4 = 100"), so the slot is `not_found`.
- `G2-CAM-C` q1b: "98" at 74.8% where the child probably wrote 48.
- **Do not retry without the silent-error count beside it:** 200 dpi (84.2% exact, 5 silently wrong), the scan's
  own dpi (76.8%), white margins (80.5%, 2 silently wrong), CLAHE/deskew — ADR 0020.

## Carried over — Nimish's calls, not blockers

- **Grade 1**: some levels hold every question there is, below a class need of 216 — `ADD.1D.WITHIN10` Easy 20,
  Hard 24; `ADD.1D.BRIDGE10` Hard 45; `SUB.1D.WITHIN20` Hard 44 (all floors: STATE, 8h).
- **W2's live n8n run**: n8n Cloud cannot reach the engine on a laptop — a hosting decision.
- **Four pedagogy questions** for Neha, Achal and Aseem: format mixing on `SUB.2D.EXCH` Hard; the provisional gold
  set's revise-or-reject case; the G1 floors; which rung place value, comparison and rounding belong on.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET` on Vercel if
  unset; the n8n owner account and its two credentials (`n8n/README.md`); GitHub branch protection (Team plan).

## Traps — do not repeat

- **Building out of order**, or **pivoting from chat**: restate, get a yes, write it into `BUILD-ORDER.md`, build.
- **Answering "is X built?" with a mechanism instead of a number.**
- **Measuring on synthetic images.** Every W3 number comes from the real pages.
- **A `blank` is a claim, not a flag**: it lands in the graph as "did not attempt".
- **Inventing a code verifier where none exists** (R7, R11, R13, X1, X2): route through a person.
- **Names stay out of the repository**: the ingest map and `gold_findings.json` live beside the papers.
- **A migration the website reads goes to live before the merge** (PR #10 merged first; rescued in minutes).
- **`legacy.remark` before 2026-09-21** would have undone people's corrections — fixed; re-marking now skips any
  answer a person settled.
- **A file the engine reads while it runs, outside `engine/`**: the server's image holds `engine/` alone. Step 8's
  story templates under `supabase/seed/` kept the live engine restarting after PR #13 (2026-09-22);
  `tests/test_image.py` now starts the engine from that folder alone.
- **Editing this file by slicing it**: a 2026-09-21 edit dropped everything after its own section; rebuilt from
  git (`970e605`).
- Still true, technical: `engine/assess/mark.py` 0% covered, imported by nothing; `legacy.PAPERS` unused;
  `apps/web/lib/queries.ts` one `regexp_replace(c.roll_no, '\D', …)` whose backslash the template literal eats;
  five `react-hooks/static-components` errors in `apps/web/app/(app)/library/page.tsx`; `legacy.py` (820+ lines),
  `cli.py` and `assess/misconceptions.py` over the 400-line ceiling.
