# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which step we are on and what "done" means. Then `STATE.md` for what
is verified. This file only says where the last session stopped.

## 2026-09-26, later — step 1: the box reader on a bent page; Textract is now the ceiling (not merged)

Branch `claude/gallant-cray-zvj5ey`, draft PR. Goal `s17` is **not green**.
- Test first: `test_a_bent_page_is_read_in_its_boxes_and_no_printed_line_reaches_the_reader` (5 smooth warps
  up to 2 mm) failed on main exactly as live did (an empty box "illegible", its shifted lines counted as ink).
- `boxes.py`: each answer's run of boxes is re-found around its recorded place (template match of the blank
  page's print, ±3 mm; `settle`); every printed pixel there, grown 0.8 mm, is removed before the ink count and
  from the strip; the strip is pencil on white, nothing else (`is_dark`). Box by box re-finding was tried and
  dropped: one printed square is too little to match on and jumped 1–2 mm wrong.
- Found on the real scan, second cause: Textract reads one pencil twice — "1405" tagged PRINTED over 1, 4, 0, 5
  tagged HANDWRITING — and the two were joined into eight digits. `readings`/`decide`: overlapping words are
  alternatives; a reading stands when every reading as long as the inked boxes agrees; disagreement goes to a
  person with both. Test: `test_two_readings_of_the_same_pencil_that_agree_stand_and_two_that_disagree_wait`.
- Measured here on the real 24 Sep file (same pages, same PDFs, same Textract; harness in the session scratchpad,
  not the repo): answers settled (written or blank) **43 → 80 of 192**. The goal's floor is 144.
- What is left, measured: 56 answers where Textract returns fewer digits than boxes hold ink (a 4 read "L", a 6
  "b", a 3 "B"/"P"), 23 under the confidence floor, 8 read as letters only, 1 disagreement; 24 on pages 1–2,
  which match their worksheet with 37–40 features against the 60 required.
- **Decision for Nimish:** Textract is a document reader and will not reach 75% on digits in boxes. The fix at
  the cause is a digit reader per box (the box is known to the tenth of a mm), voting with Textract — that is
  step 3's work, so the order needs his word before it is pulled forward.

## 2026-09-26 — where step 1 stands, and exactly what the next session does

**Order:** `BUILD-ORDER.md`, "ten steps" (agreed 2026-09-25/26). We are on **step 1**; its goal is
`goals/s17-step1-reread-both-scans.yaml`, written with Nimish before any work. Nothing else is built until it is green.

**Done and live (step 0 — the session operates without Nimish):**
- Every merge to main deploys the engine (`.github/workflows/deploy-engine.yml`, secrets `LIGHTSAIL_SSH_KEY`,
  `LIGHTSAIL_HOST`); a deploy waits for scans being read. `engine-logs.yml` (run by hand) shows the server's
  containers, memory, the reader key file's shape (masked), recent read runs and the engine log.
- The session reaches the engine at `$ENGINE_URL` with `X-Engine-Key: $ENGINE_KEY` (environment settings):
  `POST /read/file {url, actor, again}` reads a Drive scan (the run is `/runs/{id}`; a failure or a restart says so
  on the run), `GET /read/scan/{name}/copies` gives per-copy scores by roll, `GET /capture/{id}/readings` gives each
  answer's state and why it waits, `GET /worksheet/{code}/geometry` where its boxes print. The sandbox cannot reach
  Postgres (port 5432 is not HTTPS); everything live goes through the engine.
- n8n **F3 — read scans** is active (https://cornerstoneschool.app.n8n.cloud/workflow/8FI9HPbPz9LNgcC0): a file
  created in Drive folder `1A3vNmSQUFDSTXH30HyMZUAUwERwO2Val` is POSTed to `/read/file`. Credentials: "Google Drive
  account", "Header Auth account" (X-Engine-Key).
- The server's reader key: `~/.aws/credentials`, profile `[cornerstone]`, IAM user `cornerstone-textract`.

**Step 1, where it stopped:** the 24 Sep scan (Drive `13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6`) read on live with
`again=true` — 16 of 16 copies on their children (was 3) — but 132 of 192 answers "unclear". Cause, from
`/readings`: on the curved phone photos a printed box line lands ~1–2 mm off the key's place; `boxes.strip` paints
lines out at the key's place and misses them, so Textract reads them as `X`/`E`/`B`/`1` and `boxes.ink` counts them.
**Next:** in `w3_read/boxes.py`, re-align the printed blank locally around each answer (a few mm, template match)
and remove every printed pixel (the blank, dilated) before the ink count and the strip; a synthetic bent-page test
first (`test_a_bent_page_is_read_in_its_boxes_and_no_printed_line_reaches_the_reader`); prove it here on the real
scan (`/worksheet/{code}/geometry` + `/worksheet/{code}.pdf` + the Drive file + Textract, all reachable from the
sandbox) and show Nimish before/after counts **before** merging; then re-read 24 Sep, then 23 Sep (Drive
`1eBcFq8bsI-m_K37iR2OMMa2qbzrBtgu1`), then the child-wise table. The 23 Sep copies were printed bare: a re-read
keeps the child a person named (`copies._named_before`).

**Owed to Nimish, not code:** the Textract key `cornerstone-textract` was pasted in chat on 2026-09-24 and never
rotated — rotate it (new access key → server `~/.aws/credentials` via Lightsail SSH `nano`, and the environment's
`AWS_*`), then delete the old one. His Jev key (`TYPESAFE_API_KEY`, host `api.typesafe.ai`) is in the environment
settings and reaches a new session; Jev is step 8.

**Working rule Nimish set (2026-09-26):** say what each PR is for, and why, before starting work; nothing is
developed without a goal file agreed first.

## 2026-09-24, evening — a printed paper is read in its boxes; a photographed page keeps its pixels (W3 N8, N9)

- Nimish, on Advika's 24 Sep paper: "You are essentially reading some numbers from the working while you have
  only designed it as a working section. The children have written proper answers in the boxes." Root cause:
  every scan went through the old-paper reader (`ocr.answers_for`), which finds a question's printed words and
  takes the handwritten number nearest — on a paper with a working box under each question, the working. The
  renderer had always recorded where every box prints (`<pdf>.key.json`, `geometry`); nothing read by it.
- `w3_read/boxes.py`: a paper this system printed is lined up with the page it printed from (ORB + RANSAC against
  the PDF drawn at 254 dpi, no corner marks needed — a phone scan app cuts them off), each answer's boxes are cut
  out where recorded and only that strip, its printed lines painted out, goes to the reader. Code decides blank
  (pixel count), how many boxes hold ink, and whether the working space was written in (rule 5's third signal,
  now recorded in the geometry as `kind: work`). A reading stands only when its digit count equals the inked box
  count. `reading.read_pages` takes this path whenever the paper carries `geometry` + `printed` (`copies.paper`
  sets both from the key beside the PDF); a page that will not line up falls back to the old reader and says so.
- The 24 Sep file itself (fetched here from Achal's link-shared Drive file, never into the repo): 16 photographed
  pages, each 2000–3000 px, each a photo letterboxed on an A4 PDF page. Drawn at 150 dpi the QR fell to ~4 px a
  module: OpenCV read 3 of 16. `render_pdf.photo` now hands back the photograph's own pixels; `sorting.qr_of`
  tries zxing-cpp over the corner as it is, ×2, ×3, ×4 softened, three binarizers, then the old detector:
  **13 of 16** here. The last three (pages 14–16) go to the printed-code fallback (#64, Textract, on the server).
  QRs now print with the most error correction (`error="h"`); the code is still the smallest QR.
- Not run on live: this sandbox has no Textract (its AWS key is invalid) and no route to the live database, so the
  proof is the synthetic scan (`tests/test_boxes.py`, goal `s16-read-the-boxes`) plus the QR count on the real
  file. Next: `bin/engine read file ~/Downloads/"24 sept.pdf" --read` on the Mac (or the server) after merge,
  then Marking; then a child-wise table from `copies.tally`.
- **A scan arrives on its own** (N8, `w3_read/inbox.py`, `POST /read/file`): a Drive link in, the engine fetches
  the file to `~/cornerstone/assessments/inbox` (the server mounts that folder read-write now), answers at once with
  a `flow_run` id, and after answering sorts the pages by code and reads every copy printed for a child
  (`copies.read` with `names=None`: a bare copy is reported, never guessed). Marking has a "Read a scan" form
  (`readScan` in `capture/actions.ts`); `n8n/workflows/f3-read-scans.json` is the Drive-folder trigger calling the
  same route. To connect n8n: a Drive credential on the trigger, the engine's public address and key on the request.
  The file must be shared "anyone with the link" for the engine to fetch it, as Achal's are; otherwise the engine
  says so in words. Not run on live: `tests/test_inbox.py` stands the download and the reading in.

## 2026-09-24, later — a library worksheet prints for children, one code each (W2 N6, W3 N8)

- Nimish: "when you generate a worksheet for a child; that should be unique qr having the child and worksheet
  code; else how will the whole system work". Make papers already did (`assemble._hand_out`); the worksheet
  page's "Print this worksheet" button did not — it printed the bare worksheet, the same code on every copy and
  no row saying whose, which is how the 2026-09-23 Grade 2 papers were made.
- The worksheet page now prints for the children ticked (`handout.for_children`, `POST /worksheet/{code}/for.pdf`,
  `/api/worksheet/[code]/for`): one copy each with its own `CS` code, recorded for the child (`custom` purpose,
  `item_exposure`), approved in the educator's name. The bare worksheet stays as "See the worksheet", to look at.
- `engine read file <pdf> --read` reads every copy whose code names its child, no names said; `--names` only for
  copies printed bare. The answers land on the child's own printed copy.

## 2026-09-24 — library worksheet copies read for the child named on them (W3, N8)

- `engine read file <pdf> --section G2 --names "A,B,?,7,…"` — one entry per library worksheet copy in file
  order (a first name, a roll number, or `?` to skip). Every name is found in the class list before anything is
  read; each copy is cut into `data/scans/<scan>/copyNN-<code>.pdf` and read and marked by `legacy.import_scan`
  against the worksheet as it prints (`copies.printed`: each question's words and page, the name band masked).
  Every answer waits on Marking for a person; the line per copy names the child by roll, never by name.
- Root cause fixed on the way: `bank rehome` deleted old-ladder library worksheets "never handed out" — but a
  library copy records no sheet_instance, so it could not know. R2-E12 and R5-H14 were in children's hands on
  2026-09-23. They are now retired, never deleted; `sorting` and `library.pdf` read a worksheet whose skill set is
  gone. `mark` no longer needs a `kind` on the question (a bank question has none); an answer keeps its own rid.
- The 2026-09-23 Grade 2 scan: 11 copies (R8-H02 ×4, R8-H01 ×4, R2-E12 ×2, R5-H14 ×1). The names came from
  Drive's text of the file, never written to the repo; five copies wait on Nimish (three names unclear, two
  blank). Not run on live — Nimish runs it on the Mac after `bin/update-live`.

## 2026-09-24, for the morning — the update is proven on a copy of live; run it on live

`rehearse update-live` run 6 (GitHub Actions 35913118685): a copy of live (47 tables, 89,973 rows, every count
equal) put through update-live's data steps ends clean — every migration applied, every signed-off answer on a
skill, each child's skills rebuilt from their answers, Marking counting each question once; 27 answers kept but
not shown (MUL.1D 19, REASON.EXPLAIN 8 — topics not taught yet). Rehome moved 9,063 questions, 10 old papers' sums,
retired 20 unnamed stories, removed 10 old skill sets and 9 rungs; 3,010 worksheets; 270 of 270 cases covered.
Home papers this week: 16 children, 9 with a proposed paper (`engine live homes` lists each by section and roll,
now with its count of signed-off answers). **To make live the same: `bin/update-live` on the Mac** (the one
unattended write to live was refused by the auto-mode classifier). Then approve the 15 skill sets on Curriculum
(level changes withdraw ratification). Open for Nimish: `item_placement` on live (no migration), AA9 and
G3-QUIZ20's 5-digit sums (for Aseem), and how a library-worksheet copy is tied to a child.

## 2026-09-23, late night — what the rehearsal on a copy of live found

`rehearse update-live` (GitHub) copies live into its runner (47 tables, 89,973 rows, every count equal) and runs
the update there. It found: (1) live holds `item_placement`, which no migration makes (rule 9) — not copied, for
Nimish to explain or drop; (2) `engine load` never rewrites an existing skill set, so tonight's level changes (M06,
W02/W03/W06, AA9) reach live only through `engine bank levels --apply` — now in update-live after `load`, and
the 15 skills it changes wait for approval then; (3) 111 sums of three 4-digit numbers had no case — AA9 added, not
from the team's taxonomy, for Aseem; (4) 20 old model-written stories ("…had 353 mangoes and sold 26…") whose
story shape no template names — rehome now moves such a question to the skill its numbers give and retires it
with the reason, instead of stopping; it still stops for a question no skill's numbers hold. (5) old papers'
questions keep the rung they were loaded with: update-live now reloads every `supabase/seed/papers/*.json`
(a G3 word problem moves R9 → R31); G3-QUIZ20's two 5-digit sums, past the ladder, count on 4-digit addition
(R32), noted in the file for Aseem. (6) answers on untaught topics (MUL.1D 19, REASON.EXPLAIN 8) are kept and
noted by `engine live data`, not failed.

## 2026-09-23, night — the Grade 2 scan is library worksheets; the live update is rehearsed in GitHub

The Grade 2 scan (Drive 1eBcFq8…, read as text through Drive): 11 copies of library worksheets — R8-H02 ×4,
R8-H01 ×4 (3 pages each), R2-E12 ×2, R5-H14 ×1 (2 pages). A library worksheet's QR is its code, the same on
every child's copy; no roll is printed, only a handwritten Name. `engine read file` now names such a copy as its
worksheet and cuts a run of copies at the worksheet's length. **Not built: reading those copies' answers** —
nothing ties a library copy to a child but the written name, and reading a name is a PII decision (rule 6)
for Nimish: (a) a person picks the child for each copy on the website, (b) a class list's order, or (c) the
reader reads the name band. `rehearse update-live` (GitHub, workflow_dispatch) copies live into the runner,
runs update-live's data steps there and must end clean; it never writes live. Applying to live is
`bin/update-live`, run by a person — the auto-mode classifier refused an unattended write to live.

## 2026-09-23, later — live rehome refused 131 word problems; the seed was missing three story types

After #45 live's rehome refused 131 `WP1` one-step stories: "start unknown" / "change unknown" stories (W02, W03,
W06) were on no calculation skill's Advance level. A story sits with the sum the child does, as the lists already
had it (W05, W08 on SUB): W06 (lost 52, 47 left → 52 + 47) now on every ADD.* Advance, W02 and W03 (→ subtraction)
on every SUB.* Advance. A seed change: the 14 skills wait for approval again. Rehome's refusal now counts every
kind of homeless question with an example, so one run shows all of them. On live: `bin/update-live`.

## 2026-09-23, late — live rehome refused 155 questions; fixed at the labeller (start here)

Read on live (select only): `bank rehome` had never moved anything — it refused 155 old missing-number questions
(`MISSING.NUM`, stored as text alone), so 454 signed-off answers of 9 G2 children still counted on old rungs
(R9 237, R5 78, R4 60, R6 33, M1 19 …) that no taught skill shows; a child page showed only what sat on R8/R7/R11.
`child_skill_state` itself matched a rebuild (0 missing, 0 stale). Cause: `tags._missing_number` measured the
operation from the text but never the numbers' sizes, and a three-number one (`15 + □ + 13 = 42`, case M06) had
no skill. Now the text is solved into a, b, op (or addends) and measured as a new question is; M06 is in
ADD.MANY's Advance (a seed change, so ADD.MANY waits for approval again). **On live, in this order:**
`bin/engine load && bin/engine bank relabel && bin/engine bank rehome && bin/engine graph` — relabel before rehome,
since rehome places by stored tags. Marking G2 484 = 30 papers' printed questions, each counted once (checked).
`bin/update-live` now runs relabel → rehome → refill → library → graph and ends with `engine live data` (read only;
fails on an unapplied migration, answers off the shown skills, a stale graph, a question counted twice).
"See the paper": `focus_paper.preview` renders the proposed home or custom paper to PDF in a temp folder, QR `PREVIEW`,
nothing written; `GET /child/{id}/focus/paper.pdf`, `POST /child/{id}/paper/plan.pdf`, web `/api/see/[child]`, linked
from the child page, each /make/[section] row and /make/custom. Tested: its text equals the printed paper's but the QR.
Marking: an "Answers read" column and a Total row under by class, by child and by worksheet, so engine + person +
waiting visibly add up to the answers read (u3-marking spec asserts it). `engine read file <pdf>` (N8, read only): each page's QR (corner marks first, as marking does; else the page as
scanned), pages grouped per paper, each code looked up in sheet_instance. Reading the answers of a paper the
engine printed is NOT built — `legacy import` reads only papers entered as `legacy paper`. Next: Nimish runs
`read file` on the Grade 2 scan (Drive 1eBcFq8…, 31 MB); what its codes are decides the reader to build.

## 2026-09-23, evening — levels by taxonomy, old ladder gone, Curriculum a tree (start here)

Merged: L1 (#33), L2 and the old ladder's removal (#34, #35), L3 answer boxes (#36); U5 Curriculum on this branch.
**Next: U4 Papers**, then U6 → U8 → U7 → R1 (BUILD-ORDER, "First: the levels read from the taxonomy"). **On live,
once:** `bin/update-live && bin/engine load && bin/engine bank rehome && bin/engine bank refill && bin/engine bank
relabel && bin/engine library build && bin/engine graph`, then a person approves the fifteen new skills on Curriculum.
Aseem to confirm grade placement and where levels split (rows). R1 (one answer box read whole) waits until after U7.

## 2026-09-23, night — U3 Marking built (start here)

U3 is on branch `claude/gallant-cray-zvj5ey` (STATE, "U3 — Marking"). **Next: U4 Papers** — write
`goals/u4-papers.yaml` and its tests first; U4 owns the Papers layout fault on a phone (`s3`). **On live, after
merge:** `bin/update-live` applies migration `20260930090000_where_each_answer_stands.sql` (a view, and
`resolve_result` recording who judged); then open Marking. `bin/engine read waiting` now also prints "checked by a
person".

## 2026-09-23, night — U2 Children built

U2 is on branch `claude/gallant-cray-zvj5ey` (STATE, "U2 — Children"). **Next: U3 Marking** — write
`goals/u3-marking.yaml` and its tests first. **On live, after merge:** nothing to migrate; `bin/update-live` as
usual, then open Children → a grade → its class → a child. From the terminal a next paper now needs its approver:
`bin/engine week focus G2 <first name> 2026-W39 --make --by "<your name>"`. U4 and U5 own two layout faults found
failing on main: the Skill Map and a worksheet do not fit a phone (`s2`, `s3`).

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
name> 2026-W39` shows the plan; add `--make --by "<name>"` to approve and print it. **Next:** the class's weekly `prescribe` still groups by
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
