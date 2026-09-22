# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which step we are on and what "done" means. Then `STATE.md` for what
is verified. This file only says where the last session stopped.

## Night 2026-09-21 — where this session stopped

**Live:** PRs #8–#10 — pictures on the approval page (12 of 12, ≤ 1 s cold), typed answers that are not one
number, a judgement recorded as a judgement, step 6's gold (Aseem's 24 findings **confirmed by Nimish**;
`engine gold check`: 2 in the graph, 18 not yet signed off, 3 waiting, 1 read differently). `engine audit`: 0.

**Step 7 is done on branch `step-7`, PR #11** (`engine goal s7-paper-from-library` 6/6 GOAL ACHIEVED). **Before it
merges**, its two additive migrations go to live (`supabase db push --db-url "$DATABASE_URL"` → `20260927110000`,
`20260927120000`, nullable columns on `sheet_instance`) — the website code in it reads them. Then merge, then
`deploy/go-live.sh` from a HEAD equal to `origin/main`.

**Nimish is validating** (196 waiting at 19:17 IST). Step 6 (W3) closes when nothing waits, every paper is signed
off, and `engine gold check` says every finding the papers hold is in the graph. **Next build: step 8** — a question
counts for every skill it uses (`goals/s8-every-skill-a-question-uses.yaml`, ADR 0023; its two open points carry
defaults written in the goal).

**Open, for Nimish:** the reader reads the teacher's red pen on the Grade 3 photographs (2 of 12 settled answers
checked on 2026-09-21 were misread; a "3 boxes of 6 pencils" read as 3 from "(6+3)"). He decided the reader stays
as it is; proposed: mask red ink, measured with the silent-error count beside it (ADR 0020). No answer yet.

## Queued reader fixes — found on crops, held while coverage is held

- `G4-SEPW1` q7: two labelled answer boxes wider than `ocr.box_max_width` are thrown away as working area.
- `G3-SEPW1-A` q5: nine answers in nine small printed boxes, one found.
- `G4-SEPW1` q3: the child's digits sit inside the printed line ("4[6] + [5]4 = 100"), so the slot is `not_found`.
- `G2-CAM-C` q1b: "98" at 74.8% where the child probably wrote 48.
- **Do not retry without the silent-error count beside it:** 200 dpi (84.2% exact, 5 silently wrong), the scan's
  own dpi (76.8%), white margins (80.5%, 2 silently wrong), CLAHE/deskew — ADR 0020.

## Carried over — Nimish's calls, not blockers

- **Grade 1**: `ADD.1D.WITHIN10` holds 22–24 questions against a class need of 216.
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
- **Editing this file by slicing it**: a 2026-09-21 edit dropped everything after its own section; rebuilt from
  git (`970e605`).
- Still true, technical: `engine/assess/mark.py` 0% covered, imported by nothing; `legacy.PAPERS` unused;
  `apps/web/lib/queries.ts` one `regexp_replace(c.roll_no, '\D', …)` whose backslash the template literal eats;
  five `react-hooks/static-components` errors in `apps/web/app/(app)/library/page.tsx`; `legacy.py` (820+ lines),
  `cli.py` and `assess/misconceptions.py` over the 400-line ceiling.
