# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — validation, then hosting, then the graph. The reader is frozen.**

Nimish decided on 2026-09-21 (written into `BUILD-ORDER.md`): the reader stays as it is and improves
only through what people's validations teach it — no other manual effort. Every doubtful answer is
validated on the approval screen; then every uploaded sheet is 100% covered and scored; then the
graphs; then W3 closes. He agreed to one random "sure" answer per paper as a permanent spot-check.
Background is in `research/reports/Reading handwritten worksheet answers.md`; do not start the
location-first rebuild it recommends without asking him.

```
bin/engine read eval --reader ocr --runs 2   81.9% exact (68/83) · 1.2% silently wrong · no spread
bin/engine read waiting                      225 of 867 waiting · 642 settled (74%)
cd packages/engine && .venv/bin/python -m pytest      412 passed
```

**Done this session toward validation:** an unsure reading keeps the reader's best guess in
`raw_read.guess` (never marked from; the gold is unchanged). The corpus has NOT been re-read since,
so the stored readings do not carry guesses yet — re-read before the queue ships (`legacy.worked_on`
keeps every signed-off or corrected paper untouched).

**Next, in order:**
1. **Hosting** (Nimish asked for a public link so he, Neha and others can validate). Waiting on him
   for: OK to spend ~₹1,500–3,000/month on AWS Mumbai; an AWS permission for the engine's IAM user
   (`cornerstone-reader` can only call Textract) to create one App Runner service and one private S3
   bucket in ap-south-1; the names and emails of the people who will validate. Then: scans to the
   private bucket, `capture.path` → bucket keys, the engine on App Runner with `ENGINE_KEY`, Vercel
   given `ENGINE_URL`/`ENGINE_KEY`, each person's password set by Nimish with `bin/engine
   set-password <email>`, branch merged to `main` (Vercel production deploys from it).
2. **The validation queue** on the same link: one doubtful answer at a time across all papers, the
   guess shown for a one-click confirm, one random settled answer per paper mixed in (chosen by the
   smallest `md5(item_result.id)` per capture — stable, no schema change), a score per sheet.
3. **The live error rate:** `read waiting` reports spot-checks done and how many of the engine's sure
   answers a person changed, with an upper bound; a paper type over 1 in 100 goes to full review.

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
