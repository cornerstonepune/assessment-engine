# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **step 1 of five — `s1-site-answers`. Then 2, 3, 4, 5, in that order.**

Nimish, 2026-09-21 afternoon, after the live website failed him: the order is committed in
`BUILD-ORDER.md` ("Now: five steps"), one goal file per step (`goals/s1…s5-*.yaml`), plan in
`docs/superpowers/plans/2026-09-21-five-steps.md`. A step closes only when `bin/engine goal <name>`
is green **including its live-link criterion** — a person signed in on the public address, every
page clicked, `bin/engine live check` clean. Local green does not close a step.

**Step 1's cause is measured, not guessed (ADR 0024):** through the transaction pooler (6543, the
live road) a third query stacked on one connection never answers; `max_pipeline: 0` answers seven
at once. `STATE.md` has the runs.

**Tests now run on a local copy (ADR 0025):** `bin/testdb` copies the live rows into Supabase's own
Postgres in Docker (port 54322, `TEST_DATABASE_URL`), every table's count compared — first run:
45 tables, 45,607 rows, equal. Run it before a goal when fresh live rows matter.

**Next action:** step 1's code — `db.ts`, the pooler check, conftest guard, loading/error screens,
deadline, sign-in check, prefetch, Playwright on a production build, `engine live check` — then PR,
merge, and the live click-through.

**Step 4 (the validation queue) is W3's validation step.** The reader stays frozen; the corpus is
re-read only to carry guesses (`raw_read.guess` is written by the reader already; 0 of 225 waiting
answers carry one today because the corpus has not been re-read since).

```
bin/engine read eval --reader ocr --runs 2   81.9% exact (68/83) · 1.2% silently wrong · no spread
bin/engine read waiting                      225 of 867 waiting · 642 settled (74%)
```

**`main` is locked on this Mac, not on GitHub:** `.git/hooks/pre-push` refuses any push to `main` (tested). GitHub branch protection on a private repo needs GitHub Team (~$4/person/month) — Nimish's call; with it, `gh api -X PUT repos/cornerstonepune/assessment-engine/branches/main/protection` (checks `engine` + `web`, enforce_admins) is the real lock. Until then: merge only a PR whose two checks are green.

**The repository is PUBLIC, by Nimish's decision (2026-09-21), to be revisited.** It carries children's first names tied to their work in 19 files and 6 commit messages; he was told and chose to go live first. `main` is protected on GitHub (PR + checks `engine`,`web`, admins included) while it is public.

**Shared working tree:** the "Question bank frontend" session edits the same folder and branch and
commits its own files when its user asks — never stage by `-A`; stage by path.

## Next: does the graph reach the diagnosis Aseem reached by hand?

This is W3's reason to exist (`goals/w3-read-and-graph.yaml`: *reproduces_the_gold_diagnosis*,
*matches_all_five_reports*), and it needs no more reading. Kabir's `8500 − 3647 = 5147` must come
back out of his graph as `M_SMALL_FROM_LARGE`, and every named error in the five Grade 3 reports
(`~/cornerstone/assessments/G3/*/<Child> Maths Assessment.pdf`) must come back out of theirs.

1. **The five Grade 3 children get signed off**: 25 papers, 318 answers, **95 waiting for a person**.
   Nothing reaches the graph until a person approves the paper — the engine prepares, a person
   approves. **Who does it is Nimish's call** (him, Neha or Achal); it is the approval screen,
   `/capture/<id>`, which now says why each answer is there.
2. Build their five graphs (`bin/engine graph`), and write the runner for the two scenarios above,
   so `goal w3-read-and-graph` stops saying "declared, not met" for them.
3. What the graph gets wrong, if anything, chooses the next reader fix — not the size of a bucket.

## Queued reader fixes — found on crops, not taken, because coverage is held

Each is a page-structure bug on answers a person reads instantly (crops in `STATE.md`, 2026-09-21):
- `G4-SEPW1` q7: two answer boxes wider than `ocr.box_max_width` are thrown away as "a working
  area" although each one's printed label names its slot. A labelled box is a field at any width.
- `G3-SEPW1-A` q5: nine answers in nine small printed boxes, one found.
- `G4-SEPW1` q3: the child's digits sit inside the printed question line ("4[6] + [5]4 = 100"), so
  the question text never matches and the slot is `not_found`.
- `G2-CAM-C` q1b: "98" at 74.8% where the child probably wrote 48 — check it on the approval screen.

## Do not retry without the silent-error count beside it

200 dpi (84.2% exact, **5** silently wrong), the scan's own dpi (76.8%), white margins round a crop
(80.5%, 2 silently wrong), CLAHE/deskew. ADR 0020. The blank-page template was measured and not
built: anchoring failed 0 times in 95; the reconstruction script is `scratchpad/template.py` in the
2026-09-21 session and rebuilds in a minute from the capture rows.

## The re-read driver is rebuilt from rows, not from the papers

`ingest.py` was gone. It is not needed: every live capture already carries its file, child, paper
and the paper pages its results land on. The 30-line driver that re-reads the corpus from those
rows is in the 2026-09-21 session's scratchpad (`reingest.py`); it names no child, and rebuilding
it is one query plus `legacy.import_scan(..., again=True)`.

## Uncommitted

Everything above is on disk on `w1-goal-and-audit`, not committed — earlier sessions committed per
step; this one waits for Nimish to say so.

## Carried over — Nimish's calls, not blockers

- **Grade 1**: `ADD.1D.WITHIN10` holds 22–24 questions against a class need of 216.
- **W2's live n8n run**: n8n Cloud cannot reach the engine on a laptop. Hosting decision.
- **The plain-English pass on the skill-set screen** is still not done (formats as raw codes,
  difficulties as boxes rather than a sentence plus a worked example).
- **`ENGINE_URL`** is `http://localhost:8931` on this machine — 8000 and 8011 are held by other
  projects of yours. The engine's own default is 8000; `deploy/compose.yml` is unaffected.
- **Four pedagogy questions** for Neha, Achal and Aseem — the fourth is new:
  format mixing on `SUB.2D.EXCH` Hard; the provisional gold set's revise-or-reject case; the G1
  floors; and **which rung place value, comparison and rounding belong on**. The Grade 3 baseline
  tests all three, the ladder is addition and subtraction only, and R11 ("estimate first, judge
  reasonableness") is the only rung that carries any of their skills. Their skills are named
  correctly (`NUM.PV.01/02/03`) so the screens read right; the rung is a guess and is marked as one.
- Standing: Achal's and Neha's emails for `app.staff`; rotate the database password; `AUTH_SECRET`
  on Vercel if unset; the n8n owner account and its two credentials (`n8n/README.md`).

## Traps — do not repeat

- **Building out of order.** `BUILD-ORDER.md` rule 1 exists because three sessions did this.
- **Pivoting from chat.** Restate, get a yes, write it into `BUILD-ORDER.md`, then build.
- **Answering "is X built?" with a mechanism instead of a number.**
- **Measuring on synthetic images.** Every W3 number comes from the 118 real pages or it is not a
  number.
- **A `blank` is a claim, not a flag.** It says the child did not attempt the skill and it lands in
  the graph as exactly that. Anything the engine stands behind — `written` or `blank` — counts
  against `silently_wrong`; only `illegible` and `not_found` reach a person.
- **Running `npm run test:e2e` used to leave `engine audit` red.** Fixed, and the cause was worth
  the hour: a restore that changed content withdrew the ratification it was restoring.
- **Inventing a code verifier where none exists.** R7, R11, R13, X1, X2 have a claim code cannot
  check — say so in `philosophy` and route through a person, never a fabricated numeric check.
- **The ingest map is outside the repository on purpose.** `ingest.py`, `classify.py` and
  `classify3.py` in the session scratchpad hold the file-to-child-to-paper mapping; they name
  children, and names stay in `pii` (rule 6). Everything they established is in
  `docs/w3-paper-inventory.md` as counts, and in the database as rows. A future re-read of the
  corpus rebuilds them from the papers themselves the same way — by reading the page, never the
  file name.
- Still true, technical: `engine/assess/mark.py` is 247 statements at 0% coverage that nothing
  imports; `legacy.PAPERS` is an unused constant; `roster` is an unused import in `engine/legacy.py`;
  `apps/web/lib/queries.ts` has one `regexp_replace(c.roll_no, '\D', …)` whose backslash is eaten by
  the template literal, so it strips the letter D rather than non-digits (harmless on today's roll
  numbers, wrong in principle); five `react-hooks/static-components` errors in
  `apps/web/app/(app)/library/page.tsx`, all pre-existing.

## Side work on this branch, 2026-09-21 — the question bank on screen (not a W3 gate)

Asked for by Nimish for the founder. `/library` shows the whole bank; every question opens its own
page (as it prints, answer, every wrong answer, Correct the wording, Remove); `/worksheets/<code>`
shows a printed paper with its QR. Printing fixed on the way: 8 of 12 question kinds could not be
printed, number walls overlapped, every paper was titled "Addition and subtraction". Details and
commands in `STATE.md`. Open, and Nimish's to decide: the "combine concepts" screen (a mixed-bag
paper, or new combined questions), how a multi-skill answer counts on a child's graph, and whether
1 + 9 counts as "crossing ten". Engine-side, queued: walls and two-step problems record no
operation, so their wrong-operation mistake shows as a code.
