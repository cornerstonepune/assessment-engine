# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which workflow we are on and what "done" means. Then
`STATE.md` for what is verified. This file only says where the last session stopped.

## Where we are: **W3 — read and graph. Gate 1: Grade 3 is entered and read, and the approval screen is live.**

W1 and W2 were verified again at the start of this session and at the end of it, not assumed:

```
bin/engine goal w1-build-the-bank      6/6 criteria · GOAL ACHIEVED
bin/engine goal w2-assemble-and-print  5/5 criteria · GOAL ACHIEVED
bin/engine audit                       12 invariants · 0 violations
cd packages/engine && .venv/bin/python -m pytest        353 passed
cd apps/web && npm run test:e2e                         35 passed · 8 passed
```

## What moved

**1. Grade 3 has been read for the first time.** `G3-BASE16`, the 16-question baseline all five of
Aseem's reports are written from, is entered as 18 slots (question 3's expanded form is three
answers on one line). One whole sitting is hand-verified into the gold set off the photograph.

```
bin/engine read eval --reader ocr --runs 2
  G3-BASE16 (phone photograph)  12/18  66.7%   silently wrong 1
  Grade 2 (flat scans)          36/45  80.0%   silently wrong 0   (unchanged)
  total                         48/63  76.2%   silently wrong 1 (1.6%)
  given a row at all 100.0%     spread over 2 runs 76.2% - 76.2%
```

**The approach survives a photograph.** The geometry needed no new rule for an angled, curved,
pencil-written page: 15 of 18 questions anchored, every answer came back read or flagged, and the
educator's crosses beside two blank answers were correctly ignored. What the photograph broke was
general and had simply never been exercised — an anchor that stopped at the first token the page
had lost, an answer that had to be the last thing on its line, a `blank` claimed on an answer shape
the reader cannot read, and an eval that did not count a false blank as a silent error. All four
are fixed and measured in `STATE.md`.

**The one silent error is question 6**: the child wrote `763`, Textract read `363` at 79.8%, above
the confidence floor. Verified by eye at 14×. Not retuned from one sheet — the frontier measurement
says a floor of 85 costs Grade 2 80.0% → 73.3%.

**2. The teacher approval screen is built** — `Capture & Mark`, the queue and one paper. The page
image sits beside each reading, cropped to the exact region it was read from; a person says what
the child wrote and the engine marks it again; the correction is a new `read_correction` row and
the engine's own reading is never overwritten; and `engine read eval` now scores the reader against
the seed file **plus every correction any teacher has made**. That is the gold set growing by use
rather than by a data-entry project, and it is why this was built before the reader was finished.

`8500 − 3647 = 5147` is **not** on the baseline paper. It is question 5 of a second Grade 3 paper in
the same folder — "Grade 3–4 Mathematics Quiz", 20 questions, 24/7/2026, marked 8/20 — whose
question 18 is the `56 × 3 = 1518` of Aseem's report. Each Grade 3 child's four photographs are two
papers of two pages. That second paper is #15 in `docs/w3-paper-inventory.md` and is not entered.

## Next, in the order that removes the most risk

1. **Enter the second Grade 3 paper (#15) and the three Grade 3 September papers.** Every Grade 3
   child has 4 sittings; one paper of theirs is now readable. The 20-question quiz is where the
   gold diagnosis lives, so W3's scenario `reproduces_the_gold_diagnosis` is behind that gate.
2. **Read Kabir's remaining papers and the other four Grade 3 children**, then sign them off on the
   screen. That is the fastest path to the bar's `gold_responses_min: 300` /
   `gold_phone_photo_min: 100`, because every correction is a gold response.
3. **Wire Textract QUERIES as a second opinion** on answers geometry has already flagged, accepted
   only above the confidence floor or where it agrees with a candidate already found. The nine
   flagged answers on Grade 2 and four of Grade 3's six are the target.
4. **Then** read the whole corpus once, score it, build the graph. Not before: the reader is at
   76.2% and the bar is 97%.
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
- Still true, technical: `engine/assess/mark.py` is 247 statements at 0% coverage that nothing
  imports; `legacy.PAPERS` is an unused constant; `roster` is an unused import in `engine/legacy.py`;
  `apps/web/lib/queries.ts` has one `regexp_replace(c.roll_no, '\D', …)` whose backslash is eaten by
  the template literal, so it strips the letter D rather than non-digits (harmless on today's roll
  numbers, wrong in principle); five `react-hooks/static-components` errors in
  `apps/web/app/(app)/library/page.tsx`, all pre-existing.
