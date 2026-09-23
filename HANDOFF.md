# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which step we are on and what "done" means. Then `STATE.md` for what
is verified. This file only says where the last session stopped.

## 2026-09-23, end of session — start here

**Merged today:** #24 (bank validated against the taxonomy, five defects fixed), #25 (a child's next paper chosen
from their graph), #26 (worksheets by taxonomy), #27 (`bin/update-live`). **Open:** #28 (U1 Today + the menu).
**Live is behind main** until Nimish runs `~/cornerstone/assessment-engine/bin/update-live` (migrations → engine
server → `engine load` → relabel → refill → library build → checks). Until then live's worksheet pages break on the
missing `item.case_codes` column.

**What Nimish decided (do not re-ask):** everything counts as evidence; the engine proposes, a teacher approves every
paper; a home assignment is the child's own next paper (`assess/focus.py`) sent home, not a third kind; red / amber /
green read the graph's states (`apps/web/lib/rag.ts`); the website is six areas built one at a time, then U8 (how it
ran, for a teacher), then U7 (Generate questions) — BUILD-ORDER, "the website as the teacher's week".

**Next, in order:** U2 Children → U3 Marking → U4 Papers → U5 Curriculum → U6 Question bank → U8 How it ran → U7.
Each: write `goals/uN-*.yaml` (his words in `says`, each with its test) and the tests first, then the code; its own
PR; `bin/check` green; `engine done uN-…` pasted when reporting.

**Still waiting on Nimish and Aseem:** REASON.EXPLAIN levels ask only true or only false claims; R07 "does it make
sense" always "yes" (document's 704 changed to 705); estimates print the rounded numbers; §10.2 lines not cases; 23
mistake codes only on live (export into `supabase/seed/misconceptions.json`); ADD.3D.REG's outcome sentence vs its
Easy level.

## 2026-09-23, evening — the website as the teacher's week: U1 built

BUILD-ORDER has the six areas (U1–U6, U7 queued). U1 (Today + the menu) is built (STATE). **Next: U2 Children**
— write `goals/u2-children.yaml` and its tests first. Landing after sign-in is still `/` (Curriculum); it moves to
Today when U5 moves Curriculum to its own address.

## 2026-09-23, later still — worksheets by taxonomy (goal s12-worksheets-by-taxonomy)

`/worksheets/taxonomy` and each worksheet's cases (STATE). **On live, after merge:** apply migration
`20260929100000_a_question_names_its_taxonomy_cases.sql`, then `bin/engine bank relabel` (it fills every question's
cases; until then the page shows every case "on no worksheet"). For Nimish and the team: 22 cases have no single
level by design; ADD.3D.REG's outcome sentence disagrees with its Easy level.

## 2026-09-23, later — the next paper chosen from the child's graph (goal s11-focus-paper)

Built on the copy (STATE): `assess/focus.py`, `w2_print/focus_paper.py`, the "Next paper, from their own work"
panel on each child's Growth page with "Make this paper". **On live, after merge and `deploy/go-live.sh`:** apply
migration `20260929090000_a_paper_made_for_one_child.sql` (as every migration reaches live), `bin/engine load` (the
`focus` config row), then open a checked child's Growth page. From the terminal: `bin/engine week focus G2 <first
name> 2026-W39` shows the plan; add `--make` to print it. **Next:** the class's weekly `prescribe` still groups by
rung — move it onto `assess.focus` too, or retire it in favour of this; then steps 9 and 10.

## 2026-09-23 — the bank validated against the taxonomy (branch `claude/gallant-cray-zvj5ey`)

Every question checked by solvers outside the engine: 0 wrong keys in 16,714. Five defects fixed with tests
(STATE, 2026-09-23): the carry-pattern tagger, school rounding, the closest-hundred always in the middle, P16's
matcher, and a new audit invariant against answers guessable by ticking one place. **On live, after the merge and
`deploy/go-live.sh`, in this order:** `bin/engine load` → `bin/engine bank relabel` → `bin/engine bank refill` →
`bin/engine library build` → `bin/engine library check` → `bin/engine bank taxonomy` → `bin/engine audit`.

**Waiting on Nimish and Aseem, each named by `engine audit` or here:**
- REASON.EXPLAIN: each level asks only true claims (Easy, Medium) or only false ones (Hard, Advance), so every tick
  on a worksheet is the same answer. Mix both in every level? A rewrite waits for approval on the Skill Map.
- R07 "does the answer make sense against the estimate": always "yes". The document's own example is a wrong but
  sensible answer ("Does 704 make sense for 398 + 307?"); the seed changed it to 705. Show a claimed answer,
  sometimes sensible, sometimes not?
- Estimates print the rounded numbers ("estimate: 660 − 250 ="), so R01–R03 never ask the child to round. Keep the
  scaffold at every level, or drop it above Easy?
- §10.2 lines no case counts (addition and subtraction words, no keywords, write the number sentence, same story
  different question) and §11's two folded errors — add as cases, or agree they are covered?
- 23 mistake codes live only on live: export their `misconception` rows into `supabase/seed/misconceptions.json`
  (needs live read access) so a database built from the repository is the live one.

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
Stop hook. **Report work done only with `engine done <goal>` pasted (CLAUDE.md rule 14).** **Next, queued before
anything else:** the next-paper rule groups answers by rung, not skill — on shared rung R9 Dhanvi's subtraction
mistakes are charged to 3-digit addition and 3-digit subtraction gets no next paper (a migration to
`next_difficulty`; write its goal with `says` first).

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
