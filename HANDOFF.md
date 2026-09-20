# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Gate 1 closed: every paper entered, every scan read. The queue is now 368 answers deep.**

W1 and W2 were verified at the start of this session and at the end of it, not assumed:

```
bin/engine goal w1-build-the-bank      6/6 criteria · GOAL ACHIEVED
bin/engine goal w2-assemble-and-print  5/5 criteria · GOAL ACHIEVED
bin/engine audit                       12 invariants · 0 violations
cd packages/engine && .venv/bin/python -m pytest        356 passed
cd apps/web && npm run test:e2e                         35 passed (1 skipped) · 8 passed
bin/engine read eval --reader ocr --runs 2              76.2% exact · 1.6% silently wrong
```

## What moved

**Every paper is entered — 16 of 16, each checked against its printed page.** Twelve were new
today. Four of them had never been seen by anyone: the Cambridge paper runs at four levels and
September Week 2 at three sets, the eighteen loose Grade 2 photographs turned out to be a whole
15-question diagnostic of their own, and each Grade 3 child's four photographs are two papers of
two pages. `docs/w3-paper-inventory.md` is the table.

**Every in-scope scan is read — 71 files, 108 pages, 0 failures.**

```
section  sittings  children  files  answers  correct  wrong  blank  to a person
G2             30        11     42      484      183     86     29          186
G3             19         5     29      385       87     58     58          182
total          49        16     71      869      270    144     87          368
```

**No child has a ladder, and that is correct.** `bin/engine graph` → `0 states`. The graph reads
confirmed evidence and nothing else; 869 answers are candidates waiting on the approval screen, and
the 218 answers that had been confirmed from the replaced vision model are superseded — still in
the database, no longer in any ladder. A migration was needed for that last part: the graph was the
one place in the system that did not honour `capture.superseded_by`.

**Three reader defects and one ladder defect, all found by running the corpus:** a stacked column
sum could not be anchored at all (4 of 10 answers on one sheet → 8 of 10 once a question may span
two printed lines); a child's answer that OCR could not turn into a number was still being called
`blank` at full confidence; `rung_for` filed "4 + 3" under R4, the 2-digit column rung, so a child
who cannot add within 10 would have been recorded as failing at place value; and the graph read
superseded evidence. All four are fixed at the cause with tests.

## Next, in the order that removes the most risk

1. **Sign off the corpus on the approval screen.** 368 answers are waiting for a person and 501 are
   marked and waiting for a signature. Nothing reaches a child's ladder until that happens, and
   every correction made there is a hand-verified response that grows the gold set — which is how
   the bar's `gold_responses_min: 300` gets met without a data-entry project.
2. **Then the flag rate, which is a layout problem, not a grade or a regime problem.** Papers with
   one answer per question flag 0–35%; fill-in-the-box grids flag 70–87%, and almost all of it is
   `illegible`: the question is found and the region holds a different number of candidates than it
   has slots. The commonest cause is a child writing the answer twice, once in the box and once on
   the printed `Answer:` line. **Collapsing candidates that agree in value is the next lever** — and
   it must be measured against the gold set first, because two boxes in one row can legitimately
   hold the same number and collapsing those trades a flagged unknown for a silent error.
3. **Textract QUERIES as a second opinion** on answers geometry has already flagged, accepted only
   above the confidence floor or where it agrees with a candidate already found.
4. **Then the graph and the five gold reports**: with the corpus signed off, `reproduces_the_gold_diagnosis`
   and `matches_all_five_reports` become runnable for the first time.
5. **Then** `n8n/workflows/f3-read-and-graph.json` and `engine read accuracy`, the two W3 criteria
   still red.

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
