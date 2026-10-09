# HANDOFF — for the next session

Read `BUILD-ORDER.md` first: it says which step we are on and what "done" means. Then `STATE.md` for what
is verified. This file only says where the last session stopped.

## 2026-10-09 — M0b: division is an operation wherever one is named

- **Slice:** M0b of BUILD-ORDER "Inserted now: multiplication and division" (W1 gate 3). Goal
  `goals/md0b-division-is-an-operation.yaml`; tests `packages/engine/tests/test_division_is_an_operation.py`.
- **M0a is merged and live:** main `4cea199`; `ci`, `migrate live` and `deploy engine` succeeded.
- **What changed:**
  - `engine/assess/operations.py` owns what an operation is: its signs, `compute`, `chain`, `divide`, and `require`,
    the sentence a kind refuses with;
  - division is in the verifier, the skill reader (`÷` → `NUM.OPS.04`), the case dimension, the old-paper sum, the
    equation parser and mistake names;
  - every kind that makes + and − refuses anything else;
  - migration `20261026090000` lets a mistake row name ÷.
- **BUILD-ORDER M0 is now M0a, M0b and M0c.** M0c: the reports and the website read a skill set as itself, not by its
  rung; a skill set's own skill is declared, not counted (`MUL.GROUPS` counts as Addition today); the website names a
  mistake by its own operation (`M_WRONG_OP` has three names, and Marking shows whichever comes first).
- **Next:** M0c, then M1.

## 2026-10-09 — M0a: every answer of a question with several answers counts

- **Slice:** M0a of BUILD-ORDER "Inserted now: multiplication and division" (W1 gate 3, reopened). Goal
  `goals/md0a-every-answer-counts.yaml`; tests `packages/engine/tests/test_every_answer.py`.
- **What changed:**
  - a library worksheet question with more than one answer is read: one slot per answer (`copies._slots`), the first
    keeps the question's number, the rest are `n.rid`;
  - a printed paper's tick or sentence never reaches the digit reader: `boxes.read_page(for_a_person=…)` hands it to a
    person with its crop and the reason;
  - every result is marked and shown against its own answer: `marking.response_of` in the engine, the SQL function
    `result_response` in the engine's and the website's queries (migration `20261025090000`);
  - an estimate is right within its own tolerance; a written reason goes to a person, never "unreadable";
  - a card says which answer it is ("answer 2 of 2 · exact", `result_part`);
  - `engine audit` names any result whose answer is not one its question asks for;
  - after a second reader's review: the report, the second reader, mistake naming, the unaligned-page fallback, the
    notebook and the card's question number each read an answer as its own (STATE.md, "M0a").
- **On live after merge:** the migration runs on its own. Copies read before stay as read: a question with several
  answers on them was never read. Sending a copy's Drive link to `POST /read/file` with `again: true` reads it afresh.
- **G1 rehearsal (main 1c777cc, run 37928964729) passed on a copy of live.** On live, Nimish runs `bin/update-live`.
  Then four skill sets wait for one approval each on Curriculum → Read and approve: `DATA.TALLY` and `MUL.GROUPS`
  (new), and `ADD.1D1D` and `REASON.EXPLAIN` (their levels rewritten, `bank levels --apply`).
- **Next:** M0b, `goals/md0b-division-is-an-operation.yaml`. ÷ is an operation wherever one is named. The first test:
  `M.predict('÷', 85, 4)` today raises `KeyError`.

## 2026-10-09 — multiplication and division: the taxonomy drafted, the build planned

- **The ask:** Nimish wants multiplication and division the way addition and subtraction were done, through the whole
  loop. Achal corrects the taxonomy, every method counts, and the remaining questions are answered by assumptions.
- **What exists now:**
  - the taxonomy draft `docs/design/multiplication-division-taxonomy.md`, also shared as a doc for Achal
    (claude.ai/code/artifact/bdba6993-2e65-4a57-a251-c2926011b5b1);
  - its cases as data, `docs/design/multiplication-division-cases.json`;
  - its generator and checker, `research/md_taxonomy.py`: 247 cases, 38 mistakes, 17 skills, 0 faults;
  - the twelve assumptions, ADR 0047;
  - the plan, BUILD-ORDER "Inserted now: multiplication and division", slices M0 to M5;
  - what was measured, STATE.md "Multiplication and division — measured before the build".
- **Nothing in the engine changed.**
- **Next:** M0. Write `goals/md0-every-answer-counts.yaml` and its tests first. The first test: a library worksheet
  question with two answers is read and marked per answer; today `w3_read/copies.py` skips it.
- **If Achal edits the doc:** carry his changes into `research/md_taxonomy.py`, rerun it, and commit both files. The
  doc is not regenerated from the script, so his comments stay.
- **Owed by people:**
  - Achal: corrections to the doc;
  - Nimish: approval of the new skills once their slice is live;
  - an educator: what each grade has been taught.

## 2026-10-06 — Grade 1 as its educator taught it to September

- Grade 1 is exactly her list (`goals/g1-taught-till-september.yaml`, STATE.md "Grade 1 as its educator taught it"):
  - 1-digit ± 1-digit;
  - 2-digit ± 1-digit or 2-digit, with no exchange;
  - tally marks;
  - equal groups as repeated addition.
- **On live after merge:**
  - the migration moves the four 2-digit Easy levels to Grade 1 on its own;
  - the two new skills, their questions and their worksheets need `bin/update-live`;
  - the two new skills then need one approval each on Curriculum → Read and approve.
- **Open with the educator:** 45 + 8 needs an exchange. If Grade 1 is taught it, move 2-digit + 1-digit Medium to
  Grade 1 on that skill's page.
- **A new kind of question is proven by every browser spec, not the ones named for it.** Three specs passed here
  while `e2e.spec.ts`, which reads every kind in the bank, failed in CI on the tally (STATE.md, the same section).

## 2026-10-01 — Phase 2, PR 2: live recovers

- **A restart** marks every dead run (`runs.orphaned`).
- **A rollback** is a commit given to the deploy.
- **Rebuilds of one child** are locked per child.
- **Sign-in** refuses an email after too many wrong passwords (`sign_in.*` rows).
- **Less code** (`goals/p2-less-code.yaml`):
  - `assess/mark.py`'s dead round trip is deleted;
  - every workflow reads a setting through `core/settings.py`;
  - each colour swatch carries a mark;
  - ARCHITECTURE.md §5 points at the generated route list.
- **"One owner per rule" is traced, and nothing needed merging.** The two level rules are agreed rules with one owner
  each, and the website's judgement writes match `resolve_result`. STATE.md "Phase 2, PR 2 (continued)" has the
  detail, and what was skipped with when to add it.

## 2026-10-01 — Phase 2, PR 1: live is watched

- **`engine live watch` and `watch-live.yml`** (every 10 minutes) open the issue "Live needs a look". A limit is a
  `watch.*` threshold row.
- **Ponytail's rules are on** (Nimish, 2026-10-01: https://github.com/dietrichgebert/ponytail): the laziest solution
  that works. A `ponytail:` comment names each deliberate corner and when it would need more.
- **Phase 2's remaining PRs, trimmed by those rules:**
  - a restart marks every dead run; a rollback is a commit given to the deploy; the rebuild lock; a login limit;
  - one owner per rule;
  - dead code out, and no state shown by colour alone;
  - docs.
- **Owed by Nimish:**
  - confirm that Supabase backups are on;
  - switch to the roles (STATE.md "Phase 1, PR D");
  - decide the repository's visibility: a child's first name is in its public history.

## 2026-10-01 — Phase 1 closed: the loose ends

- **`read_cells` and `word_context` are inactive.** No engine code ever asked for either, and neither had an eval.
  `tests/test_settings.py` fails on any active prompt that no code asks for. A step that uses one makes it active once
  `engine eval` has scored it (rule 7).
- **`engine done` quotes the line that passed each criterion** (`done.evidence`), not the log printed after it.
- **Owed by Nimish, unchanged:**
  - the role switch (STATE.md "Phase 1, PR D");
  - the `item_generate` bar;
  - confirming that Supabase backups are on.

## 2026-10-01 — Phase 1 of the code review: PR E (done means every check)

- **PR E:** `engine done` runs a goal's scenarios and criteria as well as Nimish's sentences, and every eval is held to
  a threshold-row bar (`checks/bars.py`, `eval.<purpose>.<measure>`). STATE.md "Phase 1, PR E" has the detail.
- **A new prompt version** must meet its purpose's bar in `engine eval`. A new eval purpose goes in `cli.EVALS` with
  its bar rows, or `tests/test_bars.py` fails.
- **Owed by Nimish:** `item_generate` has no score on record, so no bar. Run Actions → engine eval → item_generate,
  write the score down, and add its row.

## 2026-10-01 — Phase 1 of the code review: PR D (each service its own role)

- **PR B merged (#150).** PR C is #152.
- **PR D:** a migration makes `app_web` and `app_engine`, each with only what its code needs, and the engine reads
  names only through the logged accessors. `tests/test_roles.py` reads the grants back, and CI runs the browser suite
  as the two roles. STATE.md "Phase 1, PR D" has the detail and Nimish's steps to switch live; ADR 0046 has the
  alternatives rejected.
- **A new table** gets both roles' policy, and a new ledger loses update, delete and truncate, from
  `internal.apply_conventions()` at the end of its migration. **A table the website must write** needs a grant in
  that migration, and `WEB_WRITES` in `tests/test_roles.py`.
- **Local browser runs as the roles:** give both a password on the local copy (`alter role app_web password '…'`),
  then set `TEST_WEB_DATABASE_URL` and `TEST_ENGINE_DATABASE_URL`. Without them both servers use the owner's URL, as
  before.
- **Next:** E (`engine done` runs criteria and scenarios; eval bars as threshold rows).

## 2026-10-01 — Phase 1 of the code review: PR C (the types hold)

- **PR B's first CI run failed one s4 test.** The cause was order, not flake: settling an answer on a paper's own
  page signs the paper off. The fix is in #150, and STATE.md "Phase 1, PR B" has it.
- **PR C:** pyright reads the whole engine, strict on `assess/` and `core/`. Nothing it calls wrong stands, and
  `assess/`'s missing annotations are frozen per file. The website's engine calls are typed by a route list the
  engine writes (`bin/engine contract`). STATE.md "Phase 1, PR C" has the detail.
- **After changing a route or a request model**, run `bin/engine contract`; `bin/check` fails until you do.
- **Next:** D (database roles: the website writes five tables and calls two functions, and the engine is the
  writer), E (`engine done` runs criteria and scenarios; eval bars as threshold rows).

## 2026-10-01 — Phase 1 of the code review: PR B (the browser suite in CI)

- **PR A merged** after main moved: #147 and #148, from another session, landed first. Main was merged in, and only
  `HANDOFF.md` conflicted.
- **PR B:** every browser spec runs in CI on a fresh database, and a skip fails the job. Specs seed their own rows
  through `apps/web/tests/rows.ts`. STATE.md "Phase 1, PR B" has the detail.
- **Local check:** build a fresh database with `bin/testdb fresh postgresql://…/fresh` and point TEST_DATABASE_URL
  at it. The copy holds rows from older runs that a fresh database does not, and u9's bug hid behind them.
- **Next:** C (pyright on `assess/` and `core/`, the OpenAPI contract), D (database roles), E (`engine done` runs
  criteria and scenarios; eval bars as threshold rows).

## 2026-10-01 — Phase 1 of the code review: PR A (the gates hold)

- **Phase 0 is merged and live** (#144, #145, #146): every deploy waited for CI. `engine done` proves 26 of 26 of
  Nimish's promises; it says NOT DONE only because this container cannot read live's migrations table.
- **Phase 1** (Nimish: "go ahead with phase 1") is five PRs, each with its goal:
  - **A (this one):** `goals/p1-the-gates-hold.yaml`. CI lints the website with 0 warnings and holds the engine's
    coverage to a floor. The 400-line ceiling now measures the website too. Today's 30 over-complex functions
    are frozen in `workflows.json`. `engine ratchet --base` holds each frozen number and the floor to the
    change's base commit. The pyproject's extra `-q` is gone, so a `pytest -q` criterion can print "passed".
  - **B:** the browser suite in CI on a fresh database, with 0 skipped. s7 needs its own class; e2e's G3 week
    tests and s4's readings must seed their own rows (`tests/rows.py` shows how the engine tests do it).
  - **C:** pyright strict on `assess/` and `core/`, with a ratchet on untyped arguments; the engine's OpenAPI
    schema as a contract the website's calls are typed against.
  - **D:** least-privilege database roles. Anything that needs a password is Nimish's step, written down.
  - **E:** `engine done` runs each goal's criteria and scenarios; every model eval's bar becomes a threshold row.
- **The cloud container restarts between sessions**, and nothing starts its local Postgres again (the copy lives in
  `/var/tmp/pg16-engine`). Before any test that reads the database:
  `su postgres -c "setsid /usr/lib/postgresql/16/bin/pg_ctl -D /var/tmp/pg16-engine/data -o '-p 55432 -k /var/tmp/pg16-engine -c listen_addresses=127.0.0.1' -l /var/tmp/pg16-engine/log start"`

## 2026-10-01 — a skill set is secure only when every skill of it is

- Advika's approved parent report: "One- and two-step word problems — 17 of 27 right — secure", and "Next at school:
  harder questions of it", above two word-problem mistakes. `parent_facts.facts` called a set "can do" when *any*
  skill of it was secure in the graph, and printed the whole set's count beside it; `next` said "secure already" on
  the same test.
- Now a set is "can do" only when no skill of it the child answered is short of secure (`_unsure`), the rule the report
  card already used (the weakest of its skills); `next` says "secure" only of such a set.
- Test: `test_a_skill_set_is_secure_only_when_every_skill_of_it_the_child_answered_is` (failed before, passes).
- **Owed:** every parent report written before this deploys may overstate a set; they are written again (the engine
  does not mark them out of date, since no answer changed). Advika's first.

## 2026-10-01 — the parent report prints as it reads

- Advika's report, printed from the browser (Nimish): page 1 was two-thirds empty, the last two lines took a fourth page,
  the skill dots showed as a stray "○", the example tables printed as a narrow centred column, and the header said
  "Grade 2 · G2".
- Causes, in `growth/[id]/parent/letter.tsx`: every section was `break-inside-avoid`, so any section taller than the
  space left jumped whole to the next page; Chrome drops background colours by default, so filled dots and table
  shading vanished; the example grid was `inline-grid` centred. Now an entry (a skill, an example, a tip, the footer)
  stays whole and a heading stays with what follows; the report prints its colours (`print-color-adjust: exact`); the
  question takes half the row, left-aligned; a section named for its band is not repeated after the grade.
- Checked by printing the same letter with Chromium (A4): 3 pages, none half empty. Not checked on live data.

## 2026-10-01 — Phase 0 of the code review: PR 3 of 3 (the maker makes what it shows)

- **PR 1 (#144) and PR 2 (#145) are merged.** PR 1's deploy chain ran on live: CI, then the migration, then the engine
  at 0e00b3d, its commit recorded.
- **PR 3** is P0.6: the 14 correctness findings P0.5 left (one, the roll order, went in PR 2), in
  `goals/p0-the-maker-makes-what-it-shows.yaml`, plus the `engine audit` crash. Each has a test that fails on main's
  code. STATE.md "Phase 0, PR 3" lists them.
- **Rows the website tests leave in the copy:** u6, u7, u9 and u10 now plant their questions as `legacy` (an earlier
  paper's), so the bank's recheck no longer reads them as generated sums. That is what crashed `engine audit` locally.
- **Next, after the merge:**
  - run `engine done` for the six p0 goals from main;
  - Phase 1 (gates), which starts with eslint at zero warnings and Playwright in CI on a self-seeded database.
- **For Nimish** (still open from PR 1):
  - the one live query in `goals/p0-the-database-answers-only-its-own.yaml`;
  - whether Supabase backups are on;
  - whether `.claude/settings.json` should keep pre-approving merges.

## 2026-10-01 — Phase 0 of the code review: PR 1 of 3 (papers survive a deploy; live waits for CI; functions closed)

- **The review** (2026-09-30) scored the code about 5/10 and named 12 fragile points. Nimish said "go ahead with
  phase 0".
- **Phase 0 is three PRs:**
  - **PR 1 (this one):** P0.4 papers on the server's disk, P0.3 deploy and migrate only after CI, P0.1 functions closed
    to the API's roles.
  - **PR 2:** P0.2 a staff check in every page and data layer, plus `proxy.ts`; P0.5 report counts per answer, not
    per evidence row; one roll-order function in place of 12 copies (three are wrong: `'\D'` reaches Postgres as
    `'D'`).
  - **PR 3:** P0.6 the 15 correctness findings in the maker, colours and curriculum (PRs #141–#143), the `audit.run`
    crash on an item with no "ans" response, and the rows u10's test leaves in the copy.
- **PR 2, built after PR 1:** P0.2 every page checks who asks, plus `proxy.ts`; P0.5 `answer_placed`, so an answer
  counts once, and `roll_order()`. It was committed on the branch behind PR 1, to be pushed once PR 1 merges.
- **For Nimish:**
  - Run the one live query in `goals/p0-the-database-answers-only-its-own.yaml`.
  - Confirm that Supabase backups are on.
  - Decide whether `.claude/settings.json` should keep pre-approving merges.


## 2026-10-01 — the parent report, read end to end after Advika's

Nimish: "confirm with me that you have double-checked everything on the parent report". Five more found, each with a
test that failed before its fix:
- "ready for the next step" was said of a set when any one skill of it was ready (`_every`, as secure now is).
- "nearly secure — secure once it holds on another paper" was said of a set with a skill still in a repeated mistake or
  only emerging; now never.
- a mistake's count (`report.build`, which the report card shows too) counted a wrong answer to a two-skill question
  twice; now once per answer.
- `answers` (the header's "112 answers", the summary's "has answered 112 questions") counted blank questions.
- approval and the edit were refused only by hiding the buttons: a page left open could approve a report out of date
  or one a newer draft had replaced. The engine refuses both now (409), and an out-of-date report is not printed.
The out-of-date notice no longer says only "answers signed off since": a change in how the school counts makes a
report out of date too, and every report the fixes above change goes out of date on its own once this is live.

## 2026-09-30, late night — the colours said (goal u11) and the curriculum as one table (goal u12)

- **u11:** "What the colours mean" is on Children, every class and every child, in the threshold rows' own numbers.
  Grey and never-assessed skills each carry a 5-question check. "Make this check" opens the maker with it chosen.
- **u12:** Curriculum is one table: grade → subject → topic → skill. Every row has the same columns: questions,
  worksheets, each level, children assessed, taught. s2, u5 and e2e's skill-map tests now read the table.
- **Order of shipping:** PR for u10 first (open when this was written), then u11, then u12, each merged with a merge
  commit. u11 and u12 were committed on the branch behind u10 and are replayed onto main after it merges.
- **Vercel previews:** they failed from #140 on. Their cause was U9's SQL fragment, built when `/papers` was imported:
  Preview has no DATABASE_URL. The fragment is now built when a query runs, and CI builds with no DATABASE_URL, so
  this cannot pass CI again.
- **For Nimish to decide:** "taught" is inferred from any checked answer (his words: "based on the assessments"). A
  placement check therefore marks a skill taught. The alternative is a record of what was taught, which no table
  holds yet.

## 2026-09-30, night — tables that read straight; the reader as one table (goal u10); colours and curriculum next

- **Nimish's next asks, same message:**
  - (1) the tables: done in u10;
  - (2) what red, amber, green and grey mean, stated on the page, and for grey a recommended check that places the
    child (goal u11, next);
  - (3) Curriculum as one expandable table: grade → subject → topic → skill, with columns for questions,
    worksheets, levels, children assessed and taught (goal u12).
- **Answered in chat:** changing a key re-marks that question for every child, signed-off answers included (with new
  evidence and the graph rebuilt). A person's own right/wrong call is never overwritten, and is counted as kept.

## 2026-09-30, evening — the maker (goal m3)

- **Built:** /papers/make makes class practice, class assessments or home assessments for any children of a class,
  in one of three ways: one paper for all, the same skill with different questions each, or each child's own next
  step (changeable per child). Every paper is seen first, made in the educator's name, and printed as one PDF.
  STATE.md M3.
- **Next:** once merged and deployed, try it on live: G2, three children, a class practice, one paper for all; print
  it; find the three in Papers. Then the earlier backlog (the model-testing ruling on the home-activity sentence).

## 2026-09-30, evening — Papers is one menu item and one list (goal u9); the maker next

- **Built:** Marking and Make papers are one menu item, Papers. /papers is every paper in one table: kind, class,
  child, week, stage, what waits for a person, and the score. It filters by class, child, kind, week and stage, and a
  row opens the paper. STATE.md U9.
- **#139 (the Children table)** took one more commit, 3c6dc18: each sorted heading says its true direction, and the
  click test scrolls to the row.
- **Next:** the maker (task 38). Class practice, class assessment or home assessment, for any set of children, made in
  one of three ways: one paper for all; the same skill and level with different questions each; or each child's own
  next step, with a per-child change. Built on the engine's existing paths (class pack prescribe/assemble, focus,
  custom paper, library handout). Goal file with his words first.
- **Local only:** e2e "every child's paper has its own code" needs a G3 T2W1 week the local copy does not have.

## 2026-09-30, evening — Children as a table; Papers next (goal u8)

- **Nimish asked for three screens** (his answers in the session): the Children table (done, goal u8), then Papers:
  - one menu item for Marking and Make papers, one filtered list of every paper;
  - a maker that makes class practice, class assessments or home assessments for any set of children, in one of three
    ways: the same paper for all, the same skill and level with different questions each, or each child's own next step
    with a per-child override.
  - This week and Library (the rest of the 26-27 Sep sketch) are not being built now.
- **#138 on live:** migration 20261018090000 applied 09:12 UTC, deploy green 09:17; write reports → G3 run after it.

## 2026-09-30, evening — G3 roll 5 is Grade 3 (goal s27)

- **Written on live, 07:40 UTC** (write reports, run 36684707559): 15 of 15 kept, each a draft waiting for approval.
  G2 rolls 1-9 and 11 and G3 roll 1 were rewritten, their answers having moved on. G3 rolls 2-5 were new. G2 roll 10's
  report was still true and was left alone.
- **G3 roll 5 was band G4** in class G3, so their report said "Grade 4". Nimish: "G3 roll 5 should be band G3, fix it".
  Migration 20261018090000, and a class's grade taken from most of its children.
- **Next:** after the merge's deploy, run write reports → G3; roll 5's report is due again and is rewritten as Grade 3.
  Nimish corrects the class list file, or loading it again puts G4 back (the load now says so).

## 2026-09-30, evening — every parent report that is due, written by one command (goal w4d)

- **Nimish:** "the reports havent been generated for grade 3; please go ahead and generate all the reports". A report
  was written only by pressing each child's button; G3 rolls 2-5 were signed off after 2026-09-29's reports.
- **Built:** `engine report parents` and the `write reports` workflow (band all, G2, G3 or G4).
- **Next:** after the merge's deploy, run Actions → write reports → all. Read its lines: each child "kept" or why not.
  Each kept report waits for an educator to approve it. A refusal is either the draft breaking its facts three times
  (the educator writes it) or the ₹150 daily budget (`llm.daily_budget_inr`), which is Nimish's to raise.

## 2026-09-29 — the parent report's checker: none of three models passed; code and the gold fixed (goal j5)

- **Scored on the server** behind Jev: Haiku 4.5 13/14 with 8 flagged wrongly, Sonnet 5.5 low 13/14 with 7, Opus 5.5
  low 13/14 with 3. Nothing switched on. Runs and the misses in STATE.md.
- **Fixed at the cause:** code refuses a draft naming a question the facts do not hold (the kite all three missed) and
  a summary naming an improving skill without saying it improved; Nimish ruled two gold "right" sentences wrong, and
  the gold is relabelled (18 wrong sentences). Code then Jev: 16/18, none flagged wrongly.
- **Owed after merge:** Actions → engine eval → parent_review, jev_version 1, versions 3, 4, 5 again. The cheapest at
  18/18 with none flagged wrongly is switched on with the four Jev rows. None there: look at what each flagged wrongly
  (ok7's home activity, ok3's "strong skills", ok6/e8's "can add …, and this skill has grown") — a ruling for Nimish or
  a fix at its cause, never a lower bar.

## 2026-09-30, later — the right answer shown as stored; an educator changes it for every child (goal s26, ADR 0045)

- **Nimish:** "the key can be changed by an educator, not an issue. also in any correction, the system should show what
  the right answer is as stored in the system", and "stop the model testing for now and finish these two things".
- **Built, on the branch after #135:**
  - "Right answer …" on every card and in the queue.
  - "Is the right answer wrong? Change it for every child", checked by code (`keys.check`), kept as `key_correction`
    rows that the deploy's paper step puts back (`keys.reapply`), with every answer to the question marked again.
  - `again.py` (marking again) split from `marking.py`.
  - The paper page's Jev shortlist, which never showed, is fixed.
- **Model testing paused.** The three scores are in DECISIONS-LOG. When it resumes, Nimish first rules on the
  ok7/e2/e1 home-activity sentence.
- **#135 deployed** (run 36672327168, 05:17 UTC). Its mark-again on live: 7 answers wrong → correct (G3-SEPW1-A 5a,
  5b, 11b ×2, 11c ×2; G3-SEPW1-B 9c), and G3-QUIZ20/8 held. The 04:52 rehearsal had also listed G4-SEPW1 11b and 11c;
  by 05:17 live no longer needed them changed. Something between the two runs had already settled them, most likely
  a person on the page, but nothing here shows what: worth a look on that paper.
- **Caught before merge, in this branch:** the first build marked every signed-off answer again by the engine's stored
  reading. That would have overwritten a person's pre-U3 Right / Wrong / Blank, which left no row.
  - A key change now redoes only a mark its reading explains by the old key.
  - It never changes a judgement: one made by the old key is named for the educator.
  - A deploy still redoes only what a person typed (ADR 0045 §5–6).
- **Deploy order and the rehearsal, fixed:** `deploy engine` waits for `migrate live` when the merge carries a
  migration. The rehearsal records the migrations it applies to the copy.
- **Next:** the PR is #136. Merge it once CI and the rehearsal are green. Then check that migration 20261017090000 is on
  live and the deploy is green, and do the manual step in goal s26.

## 2026-09-30 — a reading is marked by what it says; every deploy marks again (goal s25, ADR 0044)

- **#134 merged by Nimish and deployed** (run 36669517359, 04:41 UTC). The three-model checker eval is running on
  main, one model at a time (task: `parent_review`, jev_version 1, versions 3, 4, 5). The cheapest at 18/18 with
  none flagged wrongly is switched on in a follow-up; otherwise each false flag goes to Nimish or is fixed at its cause.
- **Built (this branch):** true / not true marked by meaning. `engine legacy mark-again` runs on every deploy, after
  the papers. The first deploy after merging re-marks question 11 (and 9 on G3-B) wherever a person typed "false",
  and the question 5 boxes whose sides hold, signed off or not. Its log names every answer it changed. Rehearse it on
  a copy of live first (Actions → rehearse update-live, this branch) to see the list before merging.
- **Nimish's question 4 (live, same paper, 2026-09-30) is not a key error.** 4A is the box after "48 + 35 =" (key 83),
  and on his screenshot that box is empty. The child's 78 is in the first number-line box, 4B, whose key is 78; 4C is
  83. Typed as 4A = blank, 4B = 78, 4C = 83, all three mark right.
  - The defect is the card. It shows the whole question, so it does not say which of the three boxes it means.
  - Changing 4A's key to 78, as he asked, would mark every child who wrote 83 there wrong.
  - Next: each card names its own box. After that, a key correction that code checks first. It refuses a key the
    question's own sum contradicts, and it shows how many children's marks it would change before it is saved.
- **Open for Nimish:** approve the design above for correcting a key (who may change a key for everyone).

## 2026-09-29 — question 5: a split that adds up is right (goal s24, ADR 0043)

Nimish, with the live Marking page of G3 September Week 1 Level A open at 5A/5B ("638 = 600 + [19] + [19]", both
"wrong · with working"): "this question's right answer is 19 and 19, but its showing wrong - need to correct it".
- **Built:** `assess/equation.py` (a paper's `holds` read, refused unless its own key makes it true; a box right when
  its side comes out at the total) and `marking.correct` marking an equation's boxes together from people's readings
  and the engine's settled ones. Question 5 of G3-SEPW1-A, G3-SEPW1-B and G4-SEPW1 names its equations: 26 boxes.
- **Found and fixed at the cause:** the loader filed nine sums on their files' old rungs (R8, R11) where `bank rehome`
  files them (R22, R24, R26); `update-live` only hid it by running rehome last. The loader now files a sum by its shape
  first, so every deploy can enter each paper again (`deploy-engine.yml`), with nothing to rehome after.
- **`marking.py` split at its ceiling:** naming a wrong answer's mistake is `w3_read/naming.py` (`naming.unnamed`,
  `naming.name_mistake`; the routes and tests follow).
- **Owed after merge:** the deploy enters the papers; then press Save on each box of each question 5 equation that
  shows a right split as wrong. A signed-off box is corrected by its own Save, its evidence with it (#131).
- **Merged main into the branch** (#130: CI tests against `bin/testdb fresh`; #131: a signed-off answer can be
  corrected). #131 took migration version 20261015090000, so this branch's `prompt.effort` migration is now
  20261016090000 — with the same version, `migrate live` would have counted it applied and skipped it.
- **Open, for Nimish and the school:** STATE.md (2026-09-17) called this very 600 + 19 + 19 "a wrong method reaching a
  right answer … the diagnostic signal the product exists to find". Marked right, it is not recorded. ADR 0043 lists
  the three ways; any split is what is built.
- **Found on live, not this work's:** `engine live data` → `paper CS57B729: 12 answers counted for 12 questions
  printed, 6 counted twice` (rehearse update-live run 36547703784, before any step ran). Two live captures of one sheet
  carry results for the same six questions; Marking shows them twice. Which capture to supersede is a person's call.

## 2026-09-29 — Jev: the three uses proven on live; the parent report's checker reads with Jev first (goals j4, j5)

Nimish asked where Jev is integrated, then: "I really want to integrate Jev as much as possible in all the use cases to
make it efficient, cost-light" and, on the order recommended (code first, Jev on every judgement, the model only on
what Jev is unsure of, a person signing off), "with everything you have said (no except)". The order: (1) the built uses
proven live, (2) the parent report's checker, (3) skill matching, (4) the template reviewers.
- **Done, step 1 (goal j4):** the server has `TYPESAFE_API_KEY` (engine logs now say so, never the value); the eval
  workflow offers every Jev decision; an eval Jev cannot answer fails and says why. Live: week_skills 21/24,
  story_shape 63/65 with 0 wrong keys, mistake_guess 108/120 among three with 0 slips named (runs in STATE.md).
- **Built, step 2 (goal j5), switched off:** `w4_close/parent_review.py` — code's check (now also what coins make), then
  Jev per sentence with only its facts (`parent_review.claims|mistakes|home` v1), then the model on the unsure band
  (`review.jev_wrong_below` 0.1 / `review.jev_sure_above` 0.5). Gold, code then Jev: 12/14, 0 wrong, the model to read
  49 of 310 sentences; the two misses (r1, e10) are in the unsure band.
- **Haiku alone was scored and failed at its cause** (run 36520653494: 10/14, 71 right sentences flagged, 65 of them
  a skill line under the draft's `can_do` read as "secure"). Fixed in what the reader is given, not by a bigger model:
  skill lines are asked of Jev as lines about their skill set (`parent_review.skills` v1) and handed to the model as
  `skill_lines`; code then Jev is 12/14, 0 wrong, with 16 of 310 sentences left to the model.
- **Effort per prompt row** (migration 20261016090000, `prompt.effort`, sent to the row's own model only); the
  settings loaders split into `core/settings.py` (the loader stood at its frozen ceiling; now 413).
- **Owed after merge (the session can run it: Actions from any branch):** engine eval → parent_review, jev_version 1,
  version 3 (Haiku 4.5), 4 (Sonnet 5.5, low) and 5 (Opus 5.5, low), one at a time (the server's memory). The cheapest
  at 14/14 and 0 flagged wrongly: set it and the four Jev rows `active` in the seed, with the runs in DECISIONS-LOG.
  None there: fix at the cause (a question Jev asks, the reader's instructions, or code), never lower a bar.
- **Next:** step 3, skill matching — a gold of outside questions whose skill a person confirmed first; step 4, the
  reviewers — grow their 6-case golds to ~40 first.
- **A local database without Docker** (this container had no Docker daemon): Postgres 16's binaries, `initdb` as the
  `postgres` user under /var/tmp, port 55432, roles anon/authenticated/service_role, every migration in order,
  `engine load`; then `TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/postgres`. 75 DB tests fail on
  seed data alone, on main and here alike (they want live's rows) — compare lists, not counts.


## 2026-09-29 — two questions printing the same words; a missing-digit sum beside its words

- Rudraksh's G4-SEPW2 page 2 (Nimish's screenshots): 6a, 6b, 7a, 7b all showed question 6's heading and came back
  blank. 6 and 7 both print "Write the missing digits."; `ocr.find_question` took the first line that matched for
  both. And each sum prints to the right of its words, outside the region `answers_for` looked in.
- Fixed in `ocr.py`: of lines that match as well, a question takes the first not on a row another question was found
  on (questions found in number order); a question alone on its rows that finds nothing in its column looks across
  their width, where the sum's boxes are. The dead `_in_region` went (ceiling 1002 → 999).
- Rudraksh's four answers are not signed off: a person types 8, 5, 6, 6 on Marking, or his paper is read again once
  this is live. `ocr.py`'s split into the Textract adapter and the page logic stays owed (cleanup stage 2).

## 2026-09-29 — a copy's pages are the pages they print, not where they sit in the file

- Achal's voice note, roll 7 (G2, R8-H03): the paper was photographed across two files, and the second file's two
  pages — the paper's 3 and 4 — were read as 1 and 2, against Q1–Q6's words and key, and signed off that way.
- `boxes.placed`: each photograph is the run of the worksheet's pages it fits best — layout (ruled lines) times the
  print only that page has. On the real photographs: 12 of 12 placed right; ruled lines alone put 5 of 8 photos on
  their page. A copy whose pages fit no run `read.page_margin` (1.25) times better than the next is not read; a person
  places it. `page` stays the paper's page on each answer; `file_page` is the photograph's page in the copy's file,
  and every screen that shows a photograph uses it.
- A reading that put answers on questions its pages do not hold is replaced when the file is read again, its checks
  included (`copies._misplaced`): they were made against another question. Roll 7's second file is to be read again
  once this is live, and its Q7–Q12 signed off afresh.
- `copy_scores.py` split from `copies.py` (the per-scan reports), which had passed 400 lines.
- Rudraksh's G4-SEPW2 Q6/Q7 (two questions printing the same words): fixed in the entry above.
- `engine-logs.yml` prints how the reader is doing (`profiles.report`): 2026-09-29, 1,238 checked, 693 of the 898 it
  stood behind right (77%), no kind at the 95% gate.

## 2026-09-29 — a signed-off answer can be corrected

- Nimish signed Kiyaan's Grade 3–4 quiz off with Q11 (44) and Q13 (9) read as blank. A correction to a signed-off
  answer was refused (`marking.correct` took only `candidate`), leaving only row edits, which rule 4 forbids.
- Migration `20261015090000`: `evidence_placed` (everything the graph reads) keeps only each answer's latest batch;
  `answer_evidence` is the one definition of what a marked answer is evidence of, shared by `confirm_results` and the
  new `correct_signed_off`. `POST /capture/correct` takes a signed-off answer; a refusal is a 409 with its reason. The
  paper page offers "Signed off wrongly? Correct what the child wrote" under each signed-off answer.
## 2026-09-29 — CI tests against a database built from the repository (cleanup stage 0)

- `bin/testdb fresh <url>`: plain Postgres, every migration, the seed, `bank refill`, `library build` — no live rows,
  no child. CI builds one before `pytest`, so the database tests run instead of skipping (the suite: ~8 min).
- What a clean build found, each fixed at its cause:
  - 23 mistakes named by skill sets existed only on live (made by the mistake-finding prompt); now in the seed,
    fetched read-only by `engine-logs.yml`, which prints any such gap from now on.
  - story and number-line cases never drew on a level whose numbers are set by `within` (`draw._native` left the
    size to the generator's default): no case-drawn word problem at any Advance level. Fixed; ADD.1D1D Advance's three
    contradictory cases (a 2- or 3-digit unknown in a 1-digit sum) removed from the seed.
  - six levels answered every tick in one place (DECISIONS-LOG 2026-09-29).
  - tests that read whatever live held now build their own rows (`tests/rows.py`); stale tests fixed.
- **Not yet on live, needs a person:** skill sets load `on conflict do nothing`, so ADD.1D1D Advance's case list and
  REASON.EXPLAIN's mixed truth reach live only when the sets are changed there and ratified; the bank then refills.
  The estimate question's new wording is only in questions made after the deploy; the ones already in live's bank
  keep "is your exact answer close?" until they are retired and refilled.
- **Open, stage 1:** about 35 cases across 14 levels still cannot be drawn (missing-number, exchange, R/X/SZ cases),
  none leaving a level short yet; a test that every case a level lists can be drawn comes with their fix. With it:
  find-the-mistake's "which column?" sits in one column on six Advance levels (the planted mistake fixes it: a
  forgotten carry in 2-digit + 1-digit is always in the tens), unseen by the audit because it samples one random bank
  and those levels hold too few; the audit is to measure each generator directly instead. The live engine was killed
  out of memory on 26 and 28 Sep (`engine-logs.yml`).

## 2026-09-29 — the parent report is on; educators edit; twelve reports written, none yet approved

- **On live** (#120-#127, this PR): `parent_report` v12 active; code prints every count and state, the model writes
  the words, code refuses what breaks the facts (three tries, else not kept); written in the background (the site's 30 s
  was too short); an educator edits the words ("Edit the words", held to the same facts, name kept out of the rows) and
  approves by name. Decision and score: `DECISIONS-LOG.md` 2026-09-29.
- **Written on live, 2026-09-29, none approved:** all 11 in G2 and G3 roll 1 — every child with signed-off answers.
  Read by me: G3 roll 1's home activity says "three tens and five ones to show 350" (it is 35) — an educator must edit it
  before approving. G2 roll 10 (8 answers, nothing secure) leads with what went wrong; tone for Nimish.
- **G3 rolls 2-5 have no signed-off answers** (the engine refuses to write for them). `engine-logs.yml` shows 306
  answers on the legacy scans still waiting for a person (109 read right but that kind not trusted, 90 unreadable, 57
  read wrong, 34 blank, 16 unsure). Asked Nimish where the G3 papers he validated are.
- **`parent_review`** (a second model reading each draft): built, gold set of 21 drafts / 14 wrong sentences; v1
  (sonnet-5) ran past 30 min; v2 (haiku) caught 10/14 and flagged 70 right sentences. Off; not to be switched on unless
  it scores 14/14 with none flagged wrongly.
- **Writes are one at a time** (this PR): twelve started together ran out the pooler's 15 connections.

## 2026-09-28 — step 1: a photographed page is lined up by its own print (goal s23, ADR 0042)

- Nimish asked why R31-H02 copies 01 and 02 of 24 Sep were barely read. Both had been read as old papers, 0 of 24
  answers in their boxes: the line-up (ORB, one straight map, at least 60 matched features) matched 37 and 40.
- **The corner squares he agreed to were ruled out on the photographs.** The scan app cut the top two off both copies.
- Built `w3_read/lineup.py` (step N8):
  - a first map by ORB or SIFT, whichever finds more of the page's print;
  - a better map from 24 mm tiles of print;
  - a smooth field for the curl;
  - each answer found around its own printed question.

  An answer whose print is not found goes to a person as `not_found`. `boxes.py` keeps only what is in a box.
- Measured on the 46 photographed pages of 23 and 24 Sep: every page lines up, and 324 of 324 answers are found. With
  the real reader on 24 Sep: 192 of 192 answers read in their boxes (168 before); 2 read wrong and stood behind (3).
- `test_boxes`' real-reader test no longer holds a doubt's guess to be right. The reader's guess changes when the crop
  moves by under a pixel (ADR 0042, Consequences). It now holds that every digit written reached the reader.
- **Done on live** (#114 merged and deployed; 24 Sep re-read, run d8337ebc):
  - The 5 copies nobody had worked on were read again, all 60 answers in their boxes.
  - The 11 a person had worked on, copies 01 and 02 among them, are exactly as they were: every answer on them had
    been checked or corrected by hand.
  - No memory kill.
- **Next:**
  - The 23 Sep file (Drive 1eBcFq8bsI-m_K37iR2OMMa2qbzrBtgu1) has 52 of 120 answers in their boxes on live. Locally,
    all 30 of its pages now line up and every answer is found.
  - Re-read it with `POST /read/file {again: true}` once Nimish says so (goals s17, s18).
- **For step 3:** a vote of the reader over one-pixel shifts, where a reading does not fit its inked boxes, put the
  right guess on 6 more of 24 Sep's doubts and turned one right guess wrong. Not adopted.

## 2026-09-28, W4 (step 9): the report card and the parent report; the partial re-read

- **Merged:** #107 (partial re-read), #109 (report card), then this session's PR (the parent report).
  - Goals: `u6-report-card.yaml` and `w4c-parent-report.yaml`.
  - `STATE.md` has the section "Box reader, re-reads and the loop's end".
- **Next, in order:**
  1. Run the eval on the server: Actions → **engine eval** → `parent_report`, version `1`. It scores v1 on every
     child with signed-off answers, and the bar is all of them.
  2. If it passes: make v1 active in `supabase/seed/prompts.json`, record the score in `DECISIONS-LOG.md`, merge, and
     let the deploy load it.
  3. If it fails: fix the prompt at the cause (v2), then score again. Never loosen `parent_report.check`.
  4. Once active: write Agastya's, Advika's and Dhanvi's reports (Children → the child → Parent report). Nimish reads
     them for tone before any is approved.
- **Step 1 is still open:** 23 Sep is at 72% against s17's 75% floor. Nimish decides whether to accept it or wait for
  step 3.
- **Owed by Nimish:**
  - the school's own Google sign-in for Drive in n8n (step 4);
  - rotating the AWS reader key;
  - replacing N4's 24 gold notes, which this session wrote, with real educators' notes.

## 2026-09-28, curriculum: the crosswalk built from the documents in hand; the first sample is with Akanksha

- No BUILD-ORDER step moved: the crosswalk is research-layer data shaped like ADR 0041's tables. Nothing was migrated.
  Goal `goals/crosswalk-start.yaml`, `bin/engine done crosswalk-start`.
- Cambridge Primary Maths 0096, English 0058 and Science 0097 are read word for word from other schools' copies:
  296, 581 and 311 objectives. `docs/crosswalk/tables/` holds 2,789 official statements with page and level, and
  levels and steps with ages. 1,405 of the 1,750 school objectives are placed at their grade's age on a strand; 345
  wait for the drafting method.
- The prompt Nimish asked to align on is `docs/crosswalk/drafting-method.md`. Its first output is
  `docs/crosswalk/drafts/math-number-8.json`: Grade 3, Number, 30 objectives.
- **Akanksha has the first-round sheet** (20 rows; the link is in `docs/crosswalk/review/math-number-8.sent.json`). When
  she returns it:
  1. Download it as CSV.
  2. Run `python3 research/crosswalk_decisions.py MATH.NUMBER.8 <file.csv> --by Akanksha`.
  3. Run `python3 research/crosswalk_build.py`.
  4. Redraft every "Change" from her comment, with a new method version if the method itself changes.
  Her approved rows become the gold set.
- **Owed by Nimish:**
  - his yes on the method and on the four-level scale;
  - the official Cambridge files (from Akanksha, via the School Support Hub), then from anywhere:
    `~/cornerstone/assessment-engine/bin/compare-cambridge ~/Downloads/<file>.pdf`, one or more files.
- Grade 1 is age 6: Nimish decided on 28 Sep. It is ADR 0041's decision 6.
- **For Akanksha, through the Skill Map Review** (the registry is generated there, never edited here):
  - 36 objectives with "art" replaced inside words ("PVisual arts 2");
  - Grade 4 Numeracy repeating Grade 3's titles (78 of 89);
  - projects split into fragments.
- Next, after her decisions: draft the other 20 Grade 3 Number objectives, then the rest of MATH.NUMBER, then
  English.

## 2026-09-28, curriculum: the crosswalk designed as tables (ADR 0041 proposed, no step moved, nothing built)

- Nimish asked whether the spine is incomplete, and it is. He asked for each objective, per subject and grade, to say
  what NCF-SE says, what Cambridge says and what we say, turned into a written outcome at rubric level for all grades.
  He asked what tables would make that mapping accurate.
- The design is `docs/adr/0041-the-curriculum-crosswalk-is-tables-of-statements-and-signed-claims.md`. Page:
  https://claude.ai/artifact/KW1vV2p6c9Cxq6ThfTr2iR.
- Every link and every text the school writes is a `claim`. A model may propose one; only an educator's
  `claim_decision` signs it.
- Blocked on Nimish:
  - the Cambridge Primary Maths, English and Science frameworks. The Drive has only PE (0069);
  - one rubric scale;
  - who signs each subject;
  - whether to pilot Grade 3 Maths now as data or move the tables up in BUILD-ORDER.
- Nothing was migrated: the crosswalk is not one of BUILD-ORDER's ten steps, and ADR 0037 puts the spine's tables
  after them.

## 2026-09-28 — N12: a child's report from the graph, read back against Aseem's findings (goal w4b; stacked on #96)

- `engine/w4_close/report.py`, `engine report child <id>`, `engine report gold`, `GET /report/{child_id}`. Strong,
  faulty (each named mistake with the child's own example: question, what they wrote, the right answer), unexplained
  wrongs per skill, next (W2's home area). No model. `focus_paper._words` is now public as `question_text`.
- `goals/w4-close-the-loop.yaml`'s report criterion now runs `engine report gold` (the command that exists).
- Owed: `bin/engine report gold` on the server — needs `engine gold confirm` of the transcription (Nimish).
- Waiting on Nimish: the parent note / narrative — model-drafted wording per named mistake approved once by Aseem and
  composed by code (proposed), or the workflow's "LLM one sentence per child".

## 2026-09-28 — W4 starts: Friday's class card, from the graph alone (goal w4a; BUILD-ORDER step 9)

- `engine/w4_close/card.py` (new workflow folder), `engine card build|confirm`, `GET /card/{section}/{week}`,
  `POST /card/{section}/{week}/confirm`; migration `20261014090000_the_class_card.sql` (`class_card.groups`,
  `class_card_confirmation`, append-only). Each child sits once per skill set, where weakest; reteach is grouped by the
  named mistake repeated; the home area is W2's own (`focus_paper.home_area`, split out of `plan` unchanged).
- Not verified locally: the home area on real data — the local copy has no bank, so W2's catalog is empty (the 9
  focus-paper DB tests fail on main for the same reason). Run `bin/engine card build <section> <week>` on the server.
- Next in W4: the sentence per child and the parent note (Jev chooses from sentences the school writes once — the engine
  drafts them, Aseem approves), the card on the site, then N12 reports.

## 2026-09-28 — a story in anyone's words is shaped, placed and keyed (goal j3; step 8's second Jev use)

- `w1_bank/story_shape.py`, `engine bank shape "<story>"`, `POST /bank/story/shape`, `engine eval story_shape`. Jev picks the
  shape; code does the case, the place, the numbers and the one-step key, and refuses a shape the numbers contradict.
- Eval: 63/65 shapes, 0 wrong keys of 44, three runs. Owed on the server after merge: the seed load (prompt row, threshold)
  and `bin/engine eval story_shape`. **Aseem:** "how many were not sold" — take-away or part-whole? "I think of a number,
  take away 25, add 40, get 100" — CONSTRAINT or UNKNOWN_FIRST? The taxonomy allows both; they are Jev's only two misses.
- Next Jev uses, by impact: parent-note sentences (with W4), near-duplicate questions, the working's method; reviewers
  last (their gold is 6 cases each — too few to show one model beats another).

## 2026-09-28 — N4, the week's declaration (goal n4-week-declaration; PR open)

- An educator's note in their own words → Jev, one yes/no per skill set of the grade in one call (`week_skills` v1,
  `adapters/jev.yes_no`) → ticked at `week.skill_yes_above` 0.5 → the educator confirms on /make/[section]/week →
  `week_declaration` (append-only, latest stands). Eval on 24 gold notes: exact 20/24, precision 0.933, recall 0.933.
- The gold notes were written by this session from the skill sets' words; replace them with real educators' notes.
- The prompt row reaches live with #88's `engine load --settings` on deploy.

## 2026-09-28 — step 7, second half: mistakes learned from children's answers (goal s22, ADR 0039; PR open)

- Nimish: "Whenever there is an answer that the student writes which is not found in the answer list, the system should
  create that as a mistake so that next time, when a child does that, that is found." Built: a space of column rules
  (`assess/learned_rules.py`, 540 for adding, 504 for taking away) that holds every procedural named mistake — 20,267 of
  20,267 answers on 6,000 sums; confirmed unexplained wrong answers are searched in it; a rule seen on 2+ different
  questions is proposed (`learned.propose`); a person names and adopts it (`misconception` L_…, `learned_mistake`) or
  rejects it; marking recognises adopted ones at reading, on a correction and on re-marking.
- Found and fixed in passing (on #90's branch): tests expecting a trusted kind's right answer to settle alone failed
  15% of runs once the spot-check existed — `every_kind_trusted` now sets the spot rate to 0.
- Stacked: merges after #90 and #91.



## 2026-09-28 — step 7, first half: a question's real difficulty proposes, a person decides (goal s21; PR open)

- `item_stat` (ring B) is filled from confirmed answers (`learn.item_stats`, also by `engine graph`); a question far
  off its level over `item.min_attempts` (10) answers becomes a `bank_proposal`; a person decides once
  (`bank_decision`): remove (worksheets rebuilt) or keep — Nimish's choice. The Question bank page lists them.
- **Next — step 7's second half, Nimish's ask:** an answer no named mistake explains becomes a new mistake, so the next
  child who makes it is recognised: code searches column rules that reproduce confirmed unexplained answers; a rule
  seen on two or more different questions is proposed; a person names and approves it; it then predicts like the 49.
  Goal `s22-learned-mistakes`.



## 2026-09-28 — step 4: the spot-check is a share of a trusted kind's right answers (goal s20; PR open)

- `marking.spot_check_rate` (threshold row, 0.15): once a kind is trusted, its right answers settle alone except that
  share, chosen by the answer's own ids so a re-read keeps the same sample (`marking.spot_checked`, `verdicts`, also in
  `remark`). The verdict policy moved into `marking.verdicts`; `legacy.py` 672 → 670 lines (ceiling ratcheted).
- **F3 found failing, never run on a file:** all 19 n8n executions since 2026-09-26 are the Drive poll refused
  ("Quota exceeded … Requests per minute", consumer project 498586711441 — a shared project, not the school's use).
  Nimish: give F3's Drive credential the school's own Google Cloud OAuth client. Then the live proof: a scan copied into
  folder 1A3vNmSQUFDSTXH30HyMZUAUwERwO2Val runs F3, and its copies are on Marking.


## 2026-09-28 — step 2: what a check teaches (goal s19; PR open, merges after step 1's #88)

- Built on Nimish's "continue the work": the view `answer_checked` is the one definition of a checked answer and its
  label (the engine's `checked_rows` and Marking's `readerReport` had it twice); the reader keeps each answer's crop —
  the pixels it read — beside the scans (`w3_read/crops.py`, `raw_read.crop`); Marking shows accuracy by the day papers
  were read beside the table by kind. Fixed in passing: the website's `'[\s,]'` in a JS template is `[s,]` (it
  stripped the letter s), now `[[:space:],]`.
- **Next, on merge (after #88):** the re-read of 23 and 24 Sep keeps their crops; check Marking's by-day table on live.

## 2026-09-28 — step 1: a copy is read in the layout it was printed in (goal s18, ADR 0040; PR open)

- Nimish chose "Recover layout" for 23 Sep. Cause: the worksheet PDF is cached inside the container, which every deploy
  rebuilds, so the pre-L3 layout (4 boxes an answer) was gone and 87 of 108 answers fell back to the old reader.
- Built: `render.layouts` rows (three layouts since 2026-09-21), the renderer draws any (`assess/page_css.py` split out
  of `render.py`, now off the frozen list), `library.printed`, `boxes.as_printed`, `copies._as_printed`. Every deploy now
  runs `engine load --settings` with the deployed seed mounted, so settings and prompts (the `mistake_guess` prompt from
  #84 too) are live on merge.
- **Next, on merge:** the deploy loads the settings; then `POST /read/file {again: true}` for the 23 Sep file
  (1eBcFq8bsI-m_K37iR2OMMa2qbzrBtgu1) and check the floor (s17, s18). Then step 2.

## 2026-09-28, last: the spine page redesigned around one thread (ADR 0038, no step moved)

- Nimish was "getting lost in the artifact". Every item now sits on the same five steps: why, what NCF-SE asks, in
  the grade, when, how we check. Clicking anything shows its thread through them, with each link's source marked.
  A grade's year is a grid of fortnights by subjects with the units' own names. The school day shows five parts by
  grade.
- Same link, version 3: https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg. Build it with
  `python3 research/plan_build.py && python3 research/spine_page.py`. It is held by `goals/spine-readable.yaml`
  (`bin/engine done spine-readable`).
- The threads are worked out in `research/spine_links.py`, `spine_steps.py` and `spine_thread.py`; the scripts only
  draw.
- Next: his reaction. Open points for him are in the brief's "28 Sep, redesigned" section: routines paced like
  syllabus, arts units named as briefs, and "CATs" still read as academics.

## 2026-09-28, later: the Plan view inside the spine (a brainstorm view, no step moved)

- Nimish asked for one system, not separate documents. It shows how the syllabus becomes fortnights and a day of
  learning modes, how the mix shifts by grade, and whether the hours work.
- It is now the Plan view of the spine map: https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg#plan. It is built by
  `python3 research/plan_build.py && python3 research/spine_page.py`; the design lives in
  `docs/spine/plan_design.json`.
- Next: his reaction to the modes and weekly minutes. Then the generator that turns conditions into a timetable, and
  Cambridge once the school's login gives the official frameworks.

## 2026-09-28: the indicative timetable, Grades 1–7 (a brainstorm page, no step moved)

- Nimish answered the open points: Grades 1–7, IGCSE meaning Cambridge, "cat time" dropped, an Indian school
  calendar, and 8:30–2:30. He asked for an indicative timetable, academic and non-academic, with timings and coverage.
- Page: https://claude.ai/artifact/T46QvYnMgqyJW1hKktafYH. Source: `docs/brainstorms/2026-09-28-indicative-timetable.html`.
  Its official numbers come from `python3 research/timetable_data.py` (22/22 quotes found on their page).
- Finding: the school's day and calendar give about 751 teaching hours a year against NCF-SE's 955. The page shows
  what that squeezes and which levers close the gap. The brief's "28 Sep" section has the detail.
- Next: Nimish's reaction to the proposed day and levers; then the interface that generates a timetable from
  conditions. Nothing is built into the engine: BUILD-ORDER is on step 1 of ten.

## 2026-09-27, after #73 merged: the provenance check wired in; the next objective put to Nimish (no step moved)

- **Next session: read `docs/brainstorms/2026-09-27-curriculum-skeleton.md`, starting at "27 Sep, after the merge".**
  Nimish's new asks cover: Grades 1–7 in detail; the school's own additions; a Cambridge skills gap check; and whether
  application-based teaching fits the hours, with the school day that follows. Agree the objective with him before any
  work; he asked for that in so many words.
- The provenance check now runs anywhere and is wired in. `python3 research/spine_verify.py` fetches NCERT's PDFs and
  refuses a changed file. It compares whole rows: 814/814 and 729/729. `goals/spine-traceable.yaml` holds it, and CI
  runs it on every PR. CI's first run failed when ncert.nic.in dropped a connection; the fetch now asks again (after
  2, 4, 8 and 16 s) before it gives up.
- The spine build is now deterministic; unit→skill links had been emitted in set order.

## 2026-09-27 — brainstorm: the curriculum skeleton, and provenance as a rule (no step moved, nothing built)

- **To resume this discussion in a new session, read `docs/brainstorms/2026-09-27-curriculum-skeleton.md` first.** It holds
  Nimish's asks in his words, the proposal, the verified facts and the six open questions.

- Nimish asked for a cleaner structure below the subjects: one outcome per subject and grade, combining Cambridge and
  CBSE/NCERT (best of both to Grade 6; CBSE the minimum from Grade 7), prerequisites, fortnights, three activity options per
  outcome, a video slot, lesson plans drawn from the card, and child tracking. Then: "nothing needs to be fabricated … run a
  validation agent … as part of the backend itself … anyone can trace back". Brainstorm page:
  `docs/brainstorms/2026-09-27-curriculum-skeleton.html` (published as https://claude.ai/artifact/XY5Pvbwd4vjSTgj1K2R6mE).
- **Verified, not asserted:** `research/spine_verify.py` finds NCF-SE 814/814 lines in the document and NCERT 729/729 outcomes
  on their stated page; Cambridge Primary Science 0097 (Sept 2020 edition), 297/297 objectives, parsed in the scratchpad only,
  from a copy hosted on a school website. Not yet imported: the other Cambridge frameworks, Lower Secondary, IGCSE, the CBSE
  Classes 9–10 curriculum.
- **Open, waiting on Nimish:** grade N = Cambridge Stage N? (the school's Grade 2 science units teach Stage 3 lines by keyword
  match); a pilot slice (Science and Maths, Grade 2); two levels only; the fortnight as the unit and how many in a year; one
  signing lead per subject; the official Cambridge PDFs from the school's support-site login and the CBSE baseline year.
- **Nothing to build until those are answered.** The proposal: one `official_line` table for every board, school `outcome`
  rows that cite lines clause by clause, a code validator plus a second-model flagger plus a person's signature, and a trace
  from any mark to the official page.

## 2026-09-27 — the order after step 1; Jev's first two uses; the home assessment's name (all in PRs, none merged)

Nimish: engine first, then structure, then the screens (BUILD-ORDER, PR #81); no second-curriculum engine — a
curriculum module will feed this one. "Build as many [Jev use cases] as you can where the impact is maximized."
- **#81** docs: the order, `docs/design/teacher-flow.md`, `research/2026-09-27-jev-use-cases.md`.
- **#82** "Home assessment" everywhere on the child's flow; a chosen paper prints as one too (`focus_paper.heading`).
- **#84** ADR 0036 + `adapters/jev.py` + `w1_bank/mistake_guess`: eval 109–110/120 among three, 60/60 slips NONE.
- **#85** (stacked on #84) Marking: name the mistake from Jev's shortlist; `mistake_named` (migration).
- **Owed by Nimish:** `TYPESAFE_API_KEY` in the server's `.env`; merge order #81, #82, #84, #85.
- **A local Postgres for DB tests** works in a cloud session: `postgres:17` in Docker, the three roles, every migration
  in order, `engine load`; then `TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/postgres`. On seed data
  alone 77 DB tests fail on `main` and on these branches alike (they want a copy of live's rows) — compare lists, not counts.
- **Next Jev uses, by impact:** the educator's week in words → skills (N4, with its form), `skill_match` with a gold,
  parent-note sentences (with W4), near-duplicate questions, the working's method; the reviewers last (12-case gold).

## 2026-09-26, night — the curriculum spine as one graph and a clickable map (PR #73; no step moved)

- Nimish: "do the whole exercise and even finish the next two steps of mapping NCERT and the grade-wise thing … build the
  entire system as an HTML architecture which can be clicked through like a decision tree … like a neuron, a mental map".
  Done to Grade 10: `docs/spine/spine.json` (one graph, ADR 0037 proposed), built and checked by `research/spine_build.py`,
  rendered by `research/spine_page.py`. Imported: NCF-SE 2023 goals and competencies per subject per stage; NCERT outcomes
  per class 1–10. Generated by six subject seats and checked by code: competency → capability, competency → grade,
  outcome → competency, unit → competency. Every generated link is marked "proposed" on the page.
- **ADR numbers:** main took 0035 (the digit reader); this branch's ADRs are now 0036 (school OS) and 0037 (spine).
- **Found in the school's own map (`supabase/seed/registry.json`, generated from the Skill Map Review artifact):** 64 art
  units filed under "Global perspectives" and 15 geography and history units under "Visual Arts"; a find-and-replace of
  "art" garbled words ("PVisual artsicipation"); four records merge several units (unit.115, .156, .286, .420). The spine
  relabels by content (`research/spine_council/unit_subject_corrections.json`); the registry itself must be re-extracted,
  not patched (its own rule).
- **For the founders (the seats' notes, on the page):** which language is R1, R2, R3 (the seats took English, Hindi,
  Marathi); the school runs ahead of NCF in Grades 1–2 (numbers to 1,000, fractions, history and geography); Grades 1–4
  have no music, dance or theatre unit; the art forms named are almost all non-Indian (Warli is the one local form);
  preparatory mathematics in NCF has no data-handling goal though NCERT and the school teach it.
- **Next:** the curriculum team's pass on the generated links (accept, edit, reject), subject by subject; then the organ
  that holds the spine as rows, after the ten steps.

## 2026-09-26, night — step 1 on live: 24 Sep passes, 23 Sep does not; goal s17 not green

PaddleOCR (#78) and the memory fix (#79) are live. 24 Sep: 147/192 settled (floor 144), 16/16 on a child.
23 Sep: 55/108 — its papers were printed before L3's one-box-per-digit layout, so they do not line up with today's
worksheet PDFs and fall back to the old reader. **Decision owed by Nimish** (STATE.md, "Step 1 on live"): rebuild
23 Sep's as-printed layout, find the boxes on the page instead, or leave that one batch to people. Also still his:
confirm `docs/adr/0035-bench/gold.json`; whether to change the trust rules (they, not the reader, set how many answers
wait: 727 now); rotate the Textract key.

## 2026-09-26, night (later) — PaddleOCR merged (#78) and deployed; the engine ran out of memory reading 24 Sep

The live re-read (run 816cfc35) died: the kernel killed the engine itself at 1.29 GB — as it had three times before
PaddleOCR. Fixed at the cause on `claude/waiting-breakdown` (STATE.md, "no longer runs out of memory"): 747 → 244 MB.
**Next:** merge, deploy, `POST /read/file {again: true}` for 24 Sep then 23 Sep, child-wise table. Waiting before
the re-read (engine-logs, read only): 739 — old papers 439 (140 right-but-untrusted, 133 unreadable, 99 wrong, 48
blank, 19 unsure), printed library copies 300 (167 unreadable, 50, 39, 34, 10).

## 2026-09-26, night — step 1: PaddleOCR built in (ADR 0035 accepted); not merged, not live

Nimish: "Accept ADR 0035, Paddle alone at 0.90, build it." Built on `claude/gallant-cray-zvj5ey` (PR #78); see STATE.md
"S17". Production path on the real 24 Sep answers: 125/133 exact, 112 stand at 0.90, 2 wrong. The image was built and
run here under the server's memory: reader peak 707 MB, in its own process, gone after 60 s idle.
- **Next, in order:** merge (deploys); `POST /read/file {again: true}` for 24 Sep (Drive `13Zsrf3…`) then 23 Sep
  (`1eBcFq8…`); read `/read/scan/{name}/copies` and `/capture/{id}/readings`; the goal's floor is 144 of 192 settled
  and copies 01–02 of 24 Sep (24 answers) do not line up — that is the next cause to fix, in `boxes.line_up`.
- **Still owed by Nimish:** confirm `docs/adr/0035-bench/gold.json` (the two wrong readings first); rotate the
  Textract key.
- Ruled out by measurement this session (ADR 0035): MNIST/EMNIST per box, TrOCR, Paddle tiny/mobile models, one box at
  a time, a recogniser-only second look (adds a wrong answer), crops wider than 2 mm.

## 2026-09-26, evening — step 1: off-the-shelf digit readers benchmarked on the real boxes (ADR 0035, proposed)

Nimish: benchmark TrOCR, PaddleOCR and an MNIST/EMNIST classifier against Textract on the real 24 Sep box crops
before building reader logic; use the winner; don't write our own; show him before merging. Harness, gold and every
reading: `docs/adr/0035-bench/` (crops stay out of git). 133 answers with a sure gold (the session's, by eye —
not yet a person's).
- **PaddleOCR (detect + recognise) wins**: 85% exact vs Textract 70% on the same uncleaned crops; @0.90 it stands
  behind 102 with 1 wrong, Textract 66 with 0. MNIST/EMNIST per box (55–74%, 24–25 wrong stood behind) and TrOCR
  (61% cleaned, 2% uncleaned) are out.
- **Our own `boxes.strip` cleaning is the biggest defect**: removing print grown 0.8 mm eats pencil on the lines
  (8→3, 6→",", a 3 below its box → 2). Textract alone goes 51% → 70% exact when given the uncleaned crop.
- Goal measure (settled of 192): today 81; Paddle uncleaned @0.90 119; copies 01–02 (not lining up) cap it at 168.
  **The 144 floor is not reached by a reader change alone.**
- **Waiting on Nimish before any code:** (1) accept ADR 0035 or not; (2) confirm the gold (`gold.json`,
  `copy07_q09`, `copy10_q02` first); (3) Paddle alone @0.90, or Paddle+Textract agreeing (0 wrong, 45 more to a
  person). Then: the adapter (tests first), `strip` hands the reader the photograph, PaddlePaddle's memory on
  Lightsail measured, then copies 01–02's line-up.

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

## 2026-09-26, evening — the council's pass on the Level 2 draft (no step moved)

- Nimish: "you are the best judge … run a council of three to four agents of different kinds, considering parents, teachers,
  actual behavioral outcome experts … let's not wait for that dependency, and let's do it." Four seats (educator, parent,
  developmental and measurement expert, child-rights and safeguarding) each marked all 192 behaviours Accept · Edit · Skip
  with reasons (`research/level2_council/*.json`, brief in `brief.md`). Reconciled by `research/level2_council.py` (rules
  R1–R6 in its docstring; the chair's 42 decisions and 20 additions in `chair.json`, each with a reason). Result: 94 rows
  stand as written, 90 edited, 8 retired (struck through in the sitting document, restorable), 20 added; 204 live; validator
  32/32. Change log with every seat's reason: `docs/school-os-level2-council-changes.md`. The sitting document now carries
  each seat's verdict beside every row (`docs/school-os-level2-behaviours-draft.md`, rendered from the JSON by
  `research/level2_render.py`; never edit the markdown by hand).
- **What the founders now do:** their own pass, on v2, is still the eval (proposal §6, measure 3). The council's acceptance
  (76–83% as written) is measure 4, a proxy, recorded in `STATE.md`. Their time goes first to the rows marked edited,
  retired or added, and to the eleven design rules the seats raised (proposal §9): one record is one dated occasion; a note
  holds the act alone; a note is the default and a recording the consented exception; every behaviour reachable in the
  child's own language and aids; counter-examples are read by parents; the earliest fair age on Foundational rows; one
  moment, one owner; Marathi and Hindi; kind and unafraid thin at Preparatory and Middle; parent_voice and peer_comment
  unused by choice; Grade 3 under the no-screen rule.
- **Two validator rules changed on the council's finding, deliberately:** V4's two-modes-per-cell floor is now a report
  (nine cells hold only observation notes, and the seats say that is honest); V5 also reports overlap across capabilities.
  Both in `research/level2_validate.py` and proposal §5. Nimish has not seen these two changes; he should say if he
  disagrees.
- **Done after the first commit of v2:** every Foundational row carries the development seat's earliest fair age (`from_age`,
  shown in the sitting document as "from age N"); the 20 added rows were checked again by the development and rights seats and
  the chair took every edit (`research/level2_council/ages.json`, `added_review_*.json`). The whole of v2 reproduces from the
  v1 draft (commit 82cbdb8) by the one command in `STATE.md`.

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
## 2026-09-26, later — Level 2 of the spine ratified; the founders' draft produced; the platform survey done (no step moved)

- **Against main's ten-step order (above):** this PR is research and design, not development; it moves no step, adds no
  goal file, and touches nothing under `packages/`, `supabase/`, `apps/` or `n8n/`. Its documents still say "W3, step 6"
  where they were written; read that as "no step of the current order".
- **Jev, revised.** The synthesis and ADR 0036 first said "a decision registry, no Jev"; Nimish pushed back (the other
  platform already routes a child's question with it at run time), and the position now recorded is: Jev is the
  registry's first provider for text-in, choose-from-a-list decisions at volume, behind the same gates and graduation
  as every decision; never the handwriting reader; ids only; a data-processing contract first. Main's handoff says Jev
  is step 8 and his key is in the environment.

- Nimish read the council's synthesis and the answers to its six questions, and ratified the Level 2 proposal
  (`docs/school-os-proposal-capability-behaviours.md`: prompt row, validator, eval, sitting, goal draft). Logged in
  `DECISIONS-LOG.md`. Nothing under `packages/`, `supabase/`, `apps/` or `n8n/` changed; W3 step 6 continues.
- **The founders' draft exists:** `docs/school-os-level2-behaviours-draft.md` (192 behaviours, 32 cells) with its
  machine copy `docs/school-os-level2-behaviours-draft.json`. Produced by hand with the ratified prompt, not by the
  engine; checked by `research/level2_validate.py` (first pass 25/32 cells, one regeneration, then 32/32). The three
  words carry the proposal's draft meanings until the founders write theirs.
- **Waiting on the founders:** the sitting (Accept · Edit · Skip per behaviour, two founders split by capability); their
  own one-line meanings of capable, kind and unafraid. The sitting's edits are the golden set for the engine's run.
- **Done: the subject-platform survey.** Three seats' notes in `research/research_notes/Subject learning platforms
  survey/` and the consolidated report `research/reports/Subject learning platforms survey.md` ("Buy the exports,
  keep the judgement", about 12,900 words, 225 citations). Of about seventy candidates, seven let a per-child,
  per-skill result leave the vendor: Khan Academy's Districts tier, IXL, Code.org, Lexia, Quill, Kahoot and No More
  Marking. Shortlists per subject with the conditions to confirm before purchase; social science gets no adaptive
  practice at all; no export anywhere carries the three signals, so every import is score-only and the paper
  diagnostic stays. The priced shortlist for 200 children is roughly $11,000 to $13,000 a year before IXL, Mindspark
  and No More Marking quotes: an assembled figure, not a quotation. Kriyo's website domain, flagged earlier, is still
  to be checked by Nimish.
- **Recommended and standing unless Nimish objects** (his "I am aligned" followed these): CBSE from Grade 6, not 7;
  Cambridge objectives as the grain for Grades 1–5 and NCERT outcomes as the coverage target; school tablets in school
  for Grades 4–6, home optional, nothing screen-based below Grade 4; bought software capped near five percent of the
  fee (an assumption to check); three signature experiences as archetypes: investigate, make, argue.
- **Read yesterday's NeoSapien recordings** (2026-09-25 afternoon). Two facts change the design: Jev already routes a
  child's question at run time on the other platform, with pre-built fillers covering latency; and the founders
  disagree on where personalised learning happens (home tablet vs school), on what "personalised" means, and on
  what the day optimises. Section 12 of the synthesis lists the founder decisions still open.

## 2026-09-26 — the school operating system council: research, synthesis, a proposed ADR (no gate moved)

- Nimish asked for a council on the whole school operating system, of which this engine is one part. He brought
  three documents, now in `docs/sources/`: Blueprint v2, the Student OS and Jev specification (PDF plus its
  extracted text), and the SchoolOS PRD. **W3, step 6 is unchanged; nothing under `packages/`, `supabase/`,
  `apps/` or `n8n/` was touched.**
- Nine research seats wrote sourced notes: `research/research_notes/School operating system council/` 1–9, each
  ending in a council position. One writer consolidated them into
  `research/reports/School operating system council.md`.
- The chair's synthesis is `docs/school-os-council-2026-09-26.md`. It keeps Blueprint v2 as the house reference
  with five amendments: no second runtime, no run-time agent, a decision registry without Jev, counted mastery
  rules as the truth, and gating by decision class. It proposes the order of new organs after W4. Its rejected
  alternatives are recorded in **ADR 0036, status proposed**.
- **Waiting on Nimish:** ratify, or change, ADR 0036 and the synthesis. Section 12 lists the nine decisions only
  the founders can take. The first is the board (CBSE or State Board), which decides the report format.
- **Waiting on Aseem and Achal, before W4 is written:** under NCF-FS, Grade 1–2 papers should be framed and
  reported as practice artefacts with no marks to parents (synthesis, section 11, item 1).
- **Found in the code while cross-checking, for W3's queue.** The live queue's spot-check is announced. The screen
  says "the engine was sure of this one" and shows the reading first (`capture/check/page.tsx`,
  `lib/queries-read.ts`). So it measures agreement, not automation bias. The council recommends making it blind
  (synthesis, section 11, item 2). Nothing was changed.
- **Unverified and flagged:**
  - Kriyo's domain redirecting elsewhere (one seat's finding);
  - the DPDP Rules' dates, read from a mirror of the Gazette;
  - the EU Regulation number deferring Annex III duties to 2 December 2027.

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
