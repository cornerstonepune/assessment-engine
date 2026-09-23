# BUILD-ORDER — one workflow at a time, each perfected before the next

This file is the operating system for this repository. Every session reads it first, says which
workflow and which gate it is on, and does not touch a later workflow until every gate of the
current one passes in `STATE.md`. Nimish set this on 2026-09-19 after three sessions drifted
across the map and left every part incomplete. Nothing here is a suggestion.

## Now: five steps, in this order — agreed with Nimish 2026-09-21, afternoon

Nimish opened the live website and it failed him: the Question bank never opened, the Skill Map
named its 17 skills by topic label and listed 37 more that went nowhere, no skill had a single
worksheet, and the 225 answers waiting for a person were nowhere on the site. He agreed this order:
*"Go in this order, but first commit this order so that each of these particular steps has a very
specific goal post. I don't want any constant rework happening."* A step is done when its goal
command is green — `bin/engine goal <name>` — and the next starts only then. These five come before
everything else in this file, W3's graph half included; step 4 **is** W3's validation step.

| Step | Goal file | Green means |
|---|---|---|
| 1 | `goals/s1-site-answers.yaml` | every page of the live link opens in seconds, shows it is loading the moment it is clicked, and says so in words when the database cannot answer; no test or goal run touches the live database |
| 2 | `goals/s2-skill-map-outcomes.yaml` | the 17 skills are stated as what the child can do, grouped by grade, each opening a page that shows every level as a sentence and a real question, its kinds, its mistakes and its worksheets; nothing on the map goes nowhere |
| 3 | `goals/s3-worksheet-library.yaml` | every question in the bank sits on a numbered worksheet; all 68 skill-levels (17 × 4) have at least ten; a skill shows its worksheets with a level filter; a worksheet opens and prints; a question names its worksheets |
| 4 | `goals/s4-validation-queue.yaml` | every answer the engine is unsure of is in one queue on the live link, one at a time with the child's handwriting and the engine's guess, settled in a click; a sheet shows its score when nothing on it waits |
| 5 | `goals/s5-question-bank-explained.yaml` | the Question bank says in plain words what it is and how each question ties to a skill, a level, a kind and a worksheet |

**A step's code is finished and shipped before the next step's work begins; its human gates — the live
click-through, an approval — are asked for the moment the code is live and do not hold the next step's
work. A step is called done only when they are given.**

**The gate over all five is the live link, not this Mac** (Nimish: *"I am reasonably sure you have
not checked through the elements"*). A person signs in once in the browser pane, every menu page and
link is clicked on the public address, and `bin/engine live check` shows the window clean. A local
test run, however green, does not close a step.

**Step 1 — the cause, found while writing the goal.** The live website sent several queries at once
down one connection of Supabase's *transaction* pooler, and that pooler never answers the third:
reproduced 3 of 3 with the Question bank's own four queries, and with four `select 1`s. My Mac talks
to the *session* pooler, where the same code works — so every test passed while the live page hung
for Vercel's full five minutes. One driver setting (`max_pipeline: 0`) answers seven at once in
0.2–0.5 s (ADR 0024). Also in step 1: tests and goal runs on a local copy of the database (ADR 0025;
earlier today the shared database took 127–203 s to write under 1 MB while suites ran on it), table
links that no longer pre-load every page behind them, a loading screen and an error screen, an
8-second deadline on every page, a sign-in check that reports a database failure instead of sending
the person to the login page, and `bin/engine live check` over Vercel's and Supabase's logs.

**Step 2 — the words are the engine's draft; the approval is Nimish's.** The outcome is
`skill_set.learning_objective`, rewritten for all 17 in one form: a verb first, one sentence, the
school's words, no codes. A rewrite withdraws the set's ratification (trigger
`skill_set_version_on_change`), so all 17 wait for one approval on the screen, and `engine audit`
stays red until it is given. The 37-skill registry list leaves the map. Editing on the skill page
becomes the words only: the checkbox rule editor leaves it, because it knew four of the twelve
question kinds and saving any of the other ten skills from it dropped their kinds or refused.

**Step 3 — the numbers (ADR 0026).** A worksheet is 12 questions (`assemble.items_per_sheet`) of one
skill at one level, its kinds in fair shares and grouped as they print, with an ID such as `R5-H07`.
Each level gets W = max(10, ⌈N ÷ 12⌉) worksheets, so every one of the 12,567 questions is on one:
18 worksheets with no question repeated for each of the 55 levels that hold 216; 13 for the level
that holds 145; 10 for each of the 12 Grade 1 levels, which hold 22–107 questions — all the distinct
questions their arithmetic allows (ADR 0011) — so those worksheets share questions, each question
used equally often. 1,123 worksheets. A worksheet prints on demand. A removed or corrected question
retires the worksheets it was on and new ones replace them; a worksheet already printed for a child
never changes. **Not in step 3:** a child's weekly paper being handed out *from* the library rather
than drawn afresh — that is the next change after these five, agreed separately.

**Step 4 — the queue.** The corpus is re-read first so that each unclear reading carries the
reader's best guess — the reader itself unchanged, every paper a person signed off or corrected left
untouched. Then one answer at a time: the crop, the question, the guess; confirm in one click, type
what the child wrote, or judge right / wrong / blank; one answer the engine was sure of on each paper
mixed in as a spot-check; a sheet's score once nothing on it waits; reached from the menu.

**Step 5 — the bank explains itself** in three plain sentences, and every question shows its skill,
level, kind and worksheet.

## Next: six steps after the five — agreed with Nimish 2026-09-21, evening

Nimish approved the 17 skills, started validating the waiting answers, and said: *"you start building
for the next steps, like whatever is left, with the right goals in the system, and the three parts of
the queue that we also need to solve."* The three parts are the three agreed on 2026-09-21 for after
go-live (below): a question counting for every skill it uses, questions that combine concepts, and
mixed papers. The rules of the five hold: a step is done when its goal command is green; its code
ships before the next step's work starts; a human gate is asked for the moment the code is live and
does not hold the next step's code.

| Step | Goal file | Green means |
|---|---|---|
| 6 | `goals/w3-read-and-graph.yaml`, restated | **W3 closes**, as decided the night of 2026-09-21: nothing waits, every paper is signed off and scored, the graph is built from confirmed evidence, and every mistake Aseem named by hand in the five Grade 3 reports comes back out of that child's graph |
| 7 | `goals/s7-paper-from-library.yaml` | a child's paper is a library worksheet at their skill and level that they have not sat; children at one level in one week get different ones; it prints with its QR and its worksheet ID |
| 8 | `goals/s8-every-skill-a-question-uses.yaml` + `goals/s8t-taxonomy-coverage.yaml` | ADR 0023: a question's skills come from the question; a right answer is evidence for each, a wrong one against the skill its mistake names. **Widened 2026-09-22:** every case of the team's addition & subtraction taxonomy holds a worksheet's worth of questions at the levels that own it |
| 9 | `goals/s9-combined-questions.yaml` | questions that combine two or three concepts are skill sets of their own: drafted by the engine, approved once, filled, verified, on worksheets |
| 10 | `goals/s10-mixed-papers.yaml` | one paper holds questions from two or three skill sets, each at the child's own level for that skill |
| 11 | `goals/w4-close-the-loop.yaml` | **W4**: from each child's graph, Friday's class card, a home sheet with a parent note, next week's seed; monthly, a parent report in the shape of Aseem's |

**Why this order.** Step 6 first because Nimish's validations are happening now and it turns them into
the verdict W3 exists for; it is also where the mistakes the engine cannot yet name are found (Aseem's
reports diagnose multiplication, a reversed comparison sign and a copying slip, which the 39 named
mistakes do not cover). Step 7 is "the next change after these five" agreed on 2026-09-21 afternoon.
Step 8 before 9 and 10: a combined question or a mixed paper cannot be scored until an answer can
count for more than one skill. W4 last: it reads the graph the steps before it make right. If step 6
finds single-skill scoring is what keeps a report from matching, step 8 moves up — what the graph
gets wrong chooses the next fix.

**Step 6 — the gold, and what "closes" means.** Aseem's five reports are transcribed once into rows
(`gold_finding`: the child, the skill, the named mistake, his example, his own words), keyed by
`child_id` and never by name, and Nimish confirms the transcription before it is used. `engine gold
check` then reads each child's graph against them. A finding whose evidence the scanned papers do not
hold (Kiyaan has no Week 1 paper) is listed as such and counted apart, never dropped. The reader bars
written 2026-09-20 (97% exact, 93% on photographs, 300 gold answers) are superseded by the night
decision — the reader stays as it is and every doubtful answer goes to a person (ADR 0028); the rules
those scenarios stated that still hold — rules 4, 5 and 6 — are held by the test suite and `engine audit`.

**Step 8 — the two points ADR 0023 left open, with the default the code will take unless Nimish or
Aseem says otherwise:** a wrong answer no named mistake explains counts against the skill the question
was written for, marked unexplained (reported by `engine bank unclassified`, never spread across every
skill); and a mistake's skill is a column on its `misconception` row, never a table in code.

**Step 8 — the plan, measured on the bank (2026-09-22).** Of the 12,567 active questions, about 7,350
single-operation ones (column grids, bare sums, missing numbers, one-step word problems) carry their rung's
labels — often addition *and* subtraction for a question that uses one — and the 1,296 two-step budget
problems carry "problem solving + money", never the adding and subtracting they need. Four chunks, in order,
each with its own tests:
- **8a — the skills a question uses, read from the question**: a pure function of its kind and its
  operations, where an operation's skill and a kind's own skill are rows, not a Python map; every question's
  `skill_codes` corrected to it (a derived label recomputed, as a re-entered paper is — its own ADR); audit
  invariant "no question carries a skill it does not use".
- **8b — the skill a mistake charges**: kept with each question's predicted wrong answers, because the step a
  mistake breaks depends on the question — on a budget problem "summed the costs, never took them from the
  budget" charges subtraction; on a bare subtraction every mistake does. The vocabulary row carries the default
  where the operation decides. For the kinds with more than one step the engine drafts the table (kind,
  mistake → skill) and **Nimish or Aseem approves it once**, as the gold was.
- **8c — evidence per skill**: `confirm_results` writes one evidence row per skill a right answer used; for a
  wrong answer, one per skill its named mistakes charge; an unexplained wrong answer or a blank, one row on the
  question's own skill. The evidence table already allows many rows per answer.
- **8d — the graph and the screens read it**: `engine graph` rebuilds; the Growth screen shows each skill's
  row; `engine gold check` loses no finding it already reached.

**Step 8 widened — the team's taxonomy, case by case (Nimish, 2026-09-22).** He shared the school team's
*Addition & Subtraction Assessment Skill Taxonomy* (`docs/sources/addition-subtraction-skill-taxonomy.txt`)
and said: *"Make sure that the addition section module is updated with this level of taxonomy and the
consequent questions in terms of easy, medium, and advanced … we should have vertical sums as well"*, then
*"yes — go ahead and do the needful"* to the plan below, and folded 8a–8d into the same task (*"merge this
part as well in this task"*). Measured on the live bank that morning (page:
claude.ai/artifact/769ATqK16k5iuBVyPLnhKQ): of the taxonomy's 252 cases, 112 hold at least a worksheet's 12
questions, 14 hold fewer, **126 hold none** — the shorter number never first, no 3-digit ± 1-digit, no
vertical sum in Grade 1, three or more numbers only at four digits, no missing digit, the box never first,
zero never a number in its own right, find-the-mistake planting 4 of 14 errors. Reading the levels showed
why several gaps exist at all: **a level declares rules no generator reads** — ADDSUB.2D.NOREG Advance says
`order: shorter_first` and Hard `layout: horizontal`; WORD.BUDGET's four levels ask for two to four costs
and different budgets and all four print the same three-cost problem; find-the-mistake Easy names
`planted: [M_NOCARRY]` and plants either mistake. Four levels stay (Easy / Medium / Hard / Advance — his
"easy, medium, advanced" is the settled four). Chunks after 8a–8d, in order, each with its own tests:
- **8e — the cases are rows, and one command counts them**: the taxonomy's cases as `taxonomy_case` rows
  (a combination of tags, the document's own §12 advice), the tags the cases need measured by code,
  `engine bank taxonomy` printing every case's count from the bank. Done means it says 0 missing, 0 thin.
- **8f — a level holds named cases, and a rule no generator reads is refused**: a level's rule lists the
  cases it holds; the fill draws evenly across them; `engine audit` refuses any rule key its generator does
  not read. Plain-sum levels print half in columns, half in a line, Grade 1 included.
- **8g — the kinds of question the cases need**: missing digits, the box first, equations (balance with two
  operations, the same number in two boxes, the missing sign, true or false, compare without working), fact
  families, checking with the inverse, closest estimate, is-this-answer-possible, odd or even, round to the
  hundred, add 10/100/1000, friendly pairs, break apart, three or more numbers at 1–3 digits in columns and
  in a line; the missing story shapes; ten more planted mistakes. Each with its printed page, its screen,
  its skills (8a) and its mistakes' skills (8b). Story templates move to rows (ADR 0010's debt, `words.py`).
- **8h — the levels rewritten and four skills added**: the 17 skills' levels rewritten to hold their cases;
  four new skills — missing digits · equality, inverse and checking · three or more numbers · estimating to
  the hundred and judging an answer — each an outcome sentence with four levels; all wait for **one approval
  by Nimish** on the Skill Map, as the 17 did.
- **8i — the bank refilled, the library rebuilt**: new questions by code; questions outside their level's new
  rule retired; worksheets rebuilt (≥ 10 per level, ADR 0026); papers already printed never change.
  `goals/s8t-taxonomy-coverage.yaml` and `goals/s8-every-skill-a-question-uses.yaml` both green, on the copy
  and then on the live bank.

## Inserted before step 8: the engine settles only a right answer on its own — Nimish, 2026-09-21, night

Checking Aseem's reports against the engine's own marks found it marking right answers wrong with nobody
told: 355 read as 921, 252 read as 204. A random 40 of the answers it had settled alone: every one it
called right was right; 9 of the 30 it called wrong or blank were right answers it had not read. Nimish,
on "the engine settles only right answers on its own; every wrong or blank goes to a person, with the
engine's reading shown": *"yes, let's build that part."* ADR 0029. It goes before step 8 because every
step after it reads the graph, and the graph must not hold a mark nobody checked.

| Green means | Proved by |
|---|---|
| the engine's own reading settles `correct` alone and holds `wrong` and `blank`, reading kept and offered | `tests/test_legacy.py` (the two ADR 0029 tests), `tests/test_gold.py` |
| no wrong or blank stands on the engine's reading alone, on live | `engine audit` → 0 violations |
| a held answer settles in one click on the live queue, in the person's name | `apps/web/tests/s4-validation-queue.spec.ts`, 10 of 10 |

**No paper is signed off until the data job has run on live** (`engine legacy remark --every-child`):
signing off confirms every answer that is not waiting, and until then the old marks are not waiting.

## Inserted after step 8: the reader learns from every check — Nimish, 2026-09-22, afternoon

Two children fully checked, 121 answers typed by a person, and the learning loop ADR 0007 designed on
2026-09-19 was found unbuilt: `child_reading_profile` empty, a correction changing nothing after its own
row, the reader recording nothing of what it saw when it gave up. Nimish: *"You need to definitely wire up
the engine to ensure that this effort is not going in vain and the system is learning … first tell me how
you are wiring, and then only go ahead and wire."* The wiring (ADR 0032): a notebook per child rebuilt by
code from every check; the next read of that child uses it (its own floor, routed kinds, confused digits
flagged with the reading as a one-click guess); a second reader with the child's own samples proposes for
what the first gave up on; trust earned per kind at 95%; measured per batch; proven by replay. Goal:
`goals/reader-learns.yaml`. Chunks, in order, each with its tests: **L1** the record and the notebook ·
**L2** the next read uses it · **L3** the second reader with examples, with its eval · **L4** the gate, the
report, the replay.

### Standing direction — Nimish, 2026-09-22, in his words. Read before any work on reading or the graph.

1. *"All the validations that we are doing right now should help improve the system."* Every check a
   person makes must change a later read (ADR 0032; `goals/reader-learns.yaml`). A validation that only
   settles its own row is effort in vain, and he has said so: *"This is a massive effort I'm making the
   teachers do, so it better help the case."*
2. *"After this loop is done, how the entire skill interaction happens — how the system is going to read
   the skill and how that learning loop is going to take care of itself while the system really starts
   understanding the child — is going to be extremely important."* The next design after this loop: how
   evidence becomes a reading of a skill, and how that reading keeps itself honest as more papers arrive.
3. *"The vision is not just this assessment engine. We are essentially thinking about this as a knowledge
   graph which will exist for every subject, every topic, and all the grades, right from the nursery all
   the way up to the 5th, 6th, and 7th standard. When the child grows, this entire data will just keep on
   making the engine richer about the understanding of the child and how he or she is behaving."* Every
   decision about evidence, skills and the graph is taken for that: one child's record across subjects
   and years, append-only, richer with every paper. Nothing is designed for maths alone if it could be
   designed for a subject.
4. *"When you think about the skill graph, how you show it and how the teacher sees and reads the skill
   graph, it needs to be visually easy to understand."* A graph a teacher cannot read at a glance is not
   built. (`feedback_teacher_first_screens` in memory: lanes per skill, plain sentences, codes demoted.)

## Inserted after the reader learns: the workflows made visible, and promises made commands — Nimish, 2026-09-22, night

*"I'm going to make you make an entire frontend … that shows each of the steps as a proper workflow, what is
working, and how things are connected … it should look like independent workflows which connect very well to
each other."* Then, on rules that kept being forgotten: *"Build these checks. Make it a hook … Let's first go
ahead and do the three steps."* In that order (ADR 0033): the engine laid out one folder per workflow and held
to `workflows.json` by `tests/test_layout.py`; each step marked any subject or maths only; the How it works
page drawing the map with live numbers (`goals/workflows-visible.yaml`); then `engine promises`, `engine done`
and `bin/check` run by a git hook and a Claude Code Stop hook (`goals/promises-kept.yaml`).

## Inserted now: the next paper chosen from the child's graph — Nimish, 2026-09-23

Asked whether the graph makes the child's next assessment, the answer was no: the teacher picks one skill
set for the class, the child's repeated mistakes are computed and then ignored, and combined questions and
mixed papers (steps 9, 10) are goal files only. Nimish: *"Now let's build this out … do not complicate this
thing. These are like modules … After 34 evaluations, the system is able to see that there are certain areas
where the child lags. Based on some simple, smart logic, the system is able to go ahead and choose random
questions from the skill bank that it already has. That's that."* Goal: `goals/s11-focus-paper.yaml`.

Three modules, nothing else: **`assess/focus.py`** reads the graph (pure: lagging areas, weakest first, at
most three, each a skill set and a level); **`w2_print/focus_paper.py`** draws twelve random unseen bank
questions for those areas, the child's own repeated mistake first, and prints them as a paper with its QR;
**the Growth page** says which areas and why, lists the questions, and makes the paper. It reads a weak
skill by its skill as well as its rung, so subtraction mistakes on an addition rung are worked on as
subtraction — the next-paper fault queued in HANDOFF, fixed for this paper at its cause. Steps 9 and 10 are
unchanged and follow this.

## First: the levels read from the taxonomy — L1 → L2 → L3, then U5 → U4 → U6 → U8 → U7 → R1 (Nimish, 2026-09-23)

Nimish: *"even in a two-digit addition, an easy level should have just included sums with horizontal and vertical
two-digit additions … the rung level isn't making sense that way"*, *"we dont need to rebuild the bank right ? just
map the same"*, *"Mixed back can also be a part of advanced only"* (ADR 0034). Ahead of U4, one slice at a time:

| Slice | Goal file | Green means |
|---|---|---|
| L1 | `goals/s13-levels-by-taxonomy.yaml` | fifteen calculation skills, one operation and digit shape each; Easy–Hard straight calculation, Advance mixed; all 269 cases placed; the bank re-homed, none lost; worksheets one skill and level each |
| L2 | `goals/s14-graph-by-skill.yaml` | a child's graph, next paper and class grid read the fifteen skills: an answer counts on its question's skill (`evidence_placed`); old papers' sums placed by the bank's rule; `level_rule` names the new rungs. The replaced rungs stay as rows only because recorded answers and retired sets name them |
| L3 | `goals/s15-answer-boxes.yaml` | as many answer boxes as the answer has digits (Nimish chose this, 2026-09-23, knowing it tells the child the answer's size); more working space, most where a question takes two steps |

## Now: the website as the teacher's week — six areas, one at a time (Nimish, 2026-09-23)

Nimish: *"we need to cleanup the frontend … this UI is important as navigation and ease of approval is important"*,
then, on the four questions put to him: *"everything counts as evidence in the graph, and the system generates. The
teacher always approves, and home assignments are not a separate purpose, but they are, again, an extension of what
is being taught in the school and how the child is performing … Let's build this out properly. Create this as a
clear goalpost for every subtask … As we have the ability to keep changing, say, map or edit certain stuff, those
kinds of capabilities will need to exist also."*

**Settled:** every paper is evidence; the engine proposes, a teacher approves every paper before it prints; a
home assignment is the child's own next paper (`assess/focus.py`) sent home, not a third kind. **Red / amber /
green** reads the graph's own states, never new numbers: red = a repeating mistake or under half right
(`patterned_error`, `emerging`); amber = practising (`practising`); green = got it (`secure`, `stretch_ready`);
grey = fewer than three answers (`not_enough_yet`). The website shows; the engine decides.

The menu becomes the teacher's week. Each area is one slice: its goal file and its tests are written when it
starts, before its code; it ships in its own pull request; the next starts when its goal command is green.

| Slice | Goal file | Green means |
|---|---|---|
| U1 | `goals/u1-today.yaml` | the menu is Today · Children · Marking · Papers · Curriculum · Question bank; **Today** lists everything waiting on a teacher — answers to check, papers to sign off, class papers to approve for print, children whose work suggests a next paper, skills awaiting approval — each with its count and one click to act; nothing waiting says so |
| U2 | `goals/u2-children.yaml` | **Children**: each grade's classes, a class as children × skills in red / amber / green / grey, a child's page opening on one plain summary, their knowledge graph, repeated mistakes, the next paper proposed with approve, and their papers |
| U3 | `goals/u3-marking.yaml` | **Marking** = Capture & Mark and Check answers as one area: papers in, answers settled by the engine, checked by a person, still waiting — by class, child and worksheet — the one-click queue inside it, and how the reader is doing |
| U4 | `goals/u4-papers.yaml` | **Papers**: every paper — class assessment, class practice, the child's own next paper sent home — in one list by class, week and purpose, each proposed by the engine and approved by a teacher before it prints; the week's pack |
| U5 | `goals/u5-curriculum.yaml` | **Curriculum**: a tree — grade → subject → skill → level (Easy · Medium · Hard · Advance) → its worksheets — with the taxonomy as a second way to read it; a skill's words, a level's rule and cases edited in place and approved, as today |
| U6 | `goals/u6-question-bank.yaml` | **Question bank**: every question, filtered by grade, skill, level, kind, taxonomy case, mistake it can show, on a worksheet or not, status; a question's page holds everything about it — as printed, answer, the wrong answers and their mistakes, skills, cases, worksheets, how children did — and correct / remove, as today |
| U8 | `goals/u8-how-it-ran.yaml` | **How it ran — for a teacher, nothing a black box** (Nimish, 2026-09-23: *"a view where we actually show the 12 workflows and the states, like how they have run and what has been generated … not from an engineering point of view but from a teacher's lens … so that we are not treating anything as a black box"*). First the engine: every step records each run in `flow_run` (step, who or what started it, when, what it made — "read 14 papers, 212 answers, 38 held for a person"), from the command line as from the API. Then the page, replacing How it works: the twelve steps as this week's story in plain words — each step's last run, what it produced with a link to it, what waits on a person, what has not run and why — and a step opens its own history |
| U7 | later, not before U6 | **Generate questions**: from a skill or level, a teacher asks for new questions with a few inputs; every one verified by code before it joins the bank (ADR 0005). Queued, not started |
| R1 | after U7 | **One answer box, read whole** (Nimish, 2026-09-23: *"we should, at some point in time, move back to a place where, within the box, if the answer is written, the system should be able to recognize the answer"*): one box per answer again, the reader reading the number written in it, measured against the gold set (`engine eval read_cells`) before any paper prints that way. Until then, one box per digit of the answer (s15) |

Old addresses keep working (they open the new area) until nothing links to them.

## The four workflows, in the order they are built

The names are `ARCHITECTURE.md` §6.1's; the nodes are `docs/sources/assessment-workflow-v1.md`'s.
Each workflow is built *as a workflow*: an n8n flow (trigger → engine endpoints → validator agent
→ human gate → notify), prompts as rows with evals, thin engine functions behind endpoints, and a
screen where a person acts. "Built" means all of that, not the Python alone.

| # | Workflow | In | Out | Status |
|---|---|---|---|---|
| **W1** | Build the bank (N1–N2) | any skill on the map, its learning objective, a difficulty | hundreds of verified questions per skill × difficulty, for any topic, by rows only | **done: `engine goal w1-build-the-bank` → 10/10 scenarios, 5/5 criteria (2026-09-20)** |
| W2 | Assemble and print (N5–N7) | each child's prescription | per-child papers with QR, spares, key; the teacher approves | **goal met 2026-09-20: `engine goal w2-assemble-and-print` → 12/12 scenarios, 4/4 criteria. Its engine is proven; its output is not pilot-ready until W3 feeds it — see below. A live n8n run and the Grade 1 decision remain** |
| W3 | Read and graph (N8–N10) | scanned or photographed papers | marked answers, mistake patterns, the child's skill graph | **gate 1 closed 2026-09-20: all 16 papers entered and all 71 in-scope scans read. Reader held 2026-09-21 at 638 of 867 settled by the engine (74%), 229 for a person, gold 81.7% exact / 1.2% silently wrong — Nimish: "keep this coverage for now and move ahead". Next: the graph half — does it reach the diagnosis Aseem reached by hand.** No child has a ladder yet: nothing is signed off, and the graph reads confirmed evidence only |
| W4 | Close the loop (N11–N12 → N5) | the graph | next paper, home sheet, parent note, per child | not started |

**Sequencing, set by Nimish 2026-09-20.** W2's engine is proven, but its output is not
pilot-ready until W3 has read the 37 existing assessments and built real graphs for all 18
children. Entering each distinct paper with one slot per answer on the page — not per printed
question — is W3's first gate, and it precedes any reading. The order is therefore: enter the
papers → read the 37 sittings → 18 real graphs → then assemble for the pilot.

**Amended by Nimish 2026-09-21: the reader's coverage is held where it is (74% settled) and W3 moves to its graph half.** The reader is not worked again until the five Grade 3 graphs have been checked against Aseem's five reports; what the reader still gets wrong is then chosen by what the graph needs, not by the size of a bucket.

**Amended by Nimish 2026-09-21, later the same day: the reader is reopened, for three changes, each measured before the next** — after he read the flagged crops and an external reading spec (`Paper_Reading_Evaluation_Technical_Specification_v1`): *"it's not something that's so illegible … it should have actually been identified."* (1) a stencil per paper: the blank page rebuilt from the children's copies, each scan aligned to it, the child's writing told from the paper by what the blank does not hold; (2) answers that are not numbers — a closed list per question, and ticks in a True / Not true table; (3) a vision model's second read of a doubtful answer, shown the child's ink alone and never the question. After each: `engine read eval` (silently wrong may not rise) and `engine read waiting` on a re-read of every paper nobody has signed off.

**Decided by Nimish 2026-09-21, night — this supersedes the reopened-reader amendment above.** The reader stays as it is (81.9% on the gold, 1 silently wrong; the stencil stays parked) and is improved only by what people's validations teach it — no other manual effort, no second-adult transcription. The order: (1) every answer the engine is doubtful about is validated on the approval screen, made as fast as it can be; (2) with that, every uploaded sheet is 100% covered — each answer either settled by the engine or validated by a person — and each sheet gets its score; (3) the children's skill graphs are built from that and checked against Aseem's five reports; (4) W3 closes and the next phase (W4) starts. Every validation is also a checked answer: it grows the gold set the reader is measured on and the labelled crops a better reader would learn from.

QR identification is a routing lookup inside W3 — which sheet, which child — added only after
W3's reading engine is proven on the 84 real sheets. It is never mixed into the reading engine.

## Rules

1. **One workflow at a time.** No code, prompt, migration, endpoint or screen for W(n+1) while any
   W(n) gate is unchecked. Ideas for later go under *Parked* in this file, never into code.
2. **A workflow is done when its gates pass** — each gate is a command, its output, and the date,
   recorded in `STATE.md`. "Works on my machine" is not a gate.
3. **Perfect before moving.** Robust means: any topic, every skill on the map, every difficulty,
   hundreds of items, measured acceptance and cost, a validator agent, a human gate, an eval — and
   a non-technical person can watch it run as boxes in n8n.
4. **Every session** starts: read this file → `HANDOFF.md` → `STATE.md`; state "W_, gate _"; then
   work. Ends: update `STATE.md` (which gate moved, with the command and output) and `HANDOFF.md`
   (current gate, next action, nothing beyond). A session that cannot name the gate it moved has
   done nothing.
5. **Scope changes are proposed, agreed with Nimish, then written here first** — never executed
   from a chat message.

## The gates are runnable: `goals/`

Each workflow's gates live as a goal file — `goals/w1-build-the-bank.yaml` — with the sentence, the
scenarios that prove the engine does its job, and the criteria that keep the repository honest.
`bin/engine goal w1-build-the-bank` is the answer to "is it done?" (ADR 0015). W1: **10/10 scenarios,
5/5 criteria, achieved 2026-09-20.** W2, W3 and W4 must have their goal files written before their
work starts, not after.

## W1 — build the bank: the six gates

**How the bank is made (ADR 0010, supersedes ADR 0005's demotion of the samplers).** Questions
of one kind are a *pattern*, not a conversation: "two 2-digit numbers, one regroup, total under
100" is a finite space of (a, b) pairs that code enumerates from the skill set's rule, with the
answer and every misconception distractor computed, in a loop, for nothing. The model is paid
**once per pattern** — to write a small library of sentence templates with number slots for word
problems, and to judge a template's language — never once per question. Per-question model
generation is the exception, kept for the few item kinds whose language cannot be templated
(explain a claim, find the mistake) and as the oracle the enumerator is evaluated against.
The whole 64-unit bank must cost tens of rupees in model spend, not thousands; if it costs more,
the design has regressed and gate 6 fails.

Done means every line has a command and its output in `STATE.md`.

1. **Every rung has a ratifiable spec.** Every rung on the ladder — 17 today — has a `skill_set` row: name,
   learning objective, philosophy lines, formats, misconceptions, and for each of Easy, Medium,
   Hard, Advance a rule in words plus a checkable rule. Drafted by the engine for Neha and Achal to
   correct, ratified by Aseem (N1). Gate: `select count(*) from rung r where not exists (select 1
   from skill_set s where s.rung_code = r.code)` → `0`, and every row `ratified`.

   **Closed 2026-09-19 (ADR 0013).** `engine ratify --by "Nimish Shah"` → `17 ratified, 0 still
   draft`. Nimish signed all 17 himself rather than hold W2 on Aseem's calendar; Neha, Achal and
   Aseem correct them in the screen afterwards, and a content edit withdraws the ratification
   automatically, so a signature always names whoever read the words that are live.

   **Amended 2026-09-19 (Nimish; ADR 0014).** The spec's mistake list is an engine output, not a
   teacher's checklist: `engine bank misconceptions <set>` proposes every wrong method the objective
   and its rules can produce, code drops any entry whose own arithmetic is wrong and matches the
   rest to the predictors that exist, and `--apply` unions the result into the set (withdrawing its
   ratification, because a changed list has not been signed). It has two halves: code enumerates
   every named mistake the band's own numbers can produce (`assess/bands.py`, no model, no cost), and
   the prompt is asked only for what code cannot reach. Recall against a curated list is therefore a
   test, not an eval; the prompt's eval is what survives as an addition — 0.75 at ₹0.53 a skill set.
   The guard found four specs claiming mistakes the engine could not mark; see `STATE.md`.
2. **Every skill × difficulty unit is rich, produced by code from the spec.** At least 50 approved
   items in each of the 68 units (17 rungs × 4 difficulties — ~50 per skill per difficulty is the
   number agreed with the school in the workflow document), enumerated by `engine bank fill` from
   the rule in the skill-set row, answers and distractors computed, no model call for the
   arithmetic. Gate: `engine bank coverage` prints the rung × difficulty table with no cell under its target,
   and `flow_run` shows the fill's model spend for the + and − units was zero.

   **Amended 2026-09-19 (Nimish, after the measurement; ADR 0011).** The target is 50 *or the
   whole enumerable universe of that unit, whichever is smaller*. A foundational rung can hold
   less than 50: "adds within 10" has about 40 usable (a, b) pairs in total, so its four bands
   cannot each hold 50 distinct questions however the code is written. A unit in that position
   carries its own measured floor as `min_items` in its own skill-set row — a row, not a code
   exception, so the gate stays machine-checkable. A floor is only legitimate once a fresh fill
   against that unit accepts zero new items, which is the evidence that the number is the
   universe's ceiling and not merely where a run stopped.
3. **Any topic, by rows only.** A new skill set — multiplication, the workflow document's own
   example — added as rows produces verified questions with no Python change outside the
   verifier's rule checks (`ARCHITECTURE.md` §7.5's stated proof). Gate: the fill command's output
   and `git diff --stat` showing only `assess/verify.py`, if anything.
4. **Code verifies every item; the validator agent checks language once per pattern, never once
   per item.** Every enumerated item passes the code verifier (numbers exact — redundant by
   construction, kept so the gate stays honest). The `validate_item` prompt judges each *sentence
   template* when it is written (answerable, one right answer, fits the objective and the
   difficulty's words, language for the grade, no forbidden words) and a random sample of at most
   5 % of the items in each unit — a per-item model check would put the token cost straight back.
   Every rejection is counted by reason in `flow_run`. Gate: `engine eval validate_item` on a
   hand-judged gold set of templates and sampled items, pass rate recorded.

   **Amended 2026-09-19 (Nimish, after reading the external "Assessment Engine — Technical
   Architecture" proposal; three of its points folded in here because they are cheap while the
   bank is young and expensive once children are answering):**
   - **Two reviewers, not one.** The validator is two narrow, advisory prompts, each a row:
     `pedagogy_review` (does this item test the claimed skill, rung and signal?) and
     `language_review` (reading load, vocabulary, age, ambiguity, forbidden words). Both judge
     the template once and a ≤5 % item sample; neither is final authority — a person approves.
   - **Difficulty is measured, not asserted.** A band's rule is a *region* in the same dimension
     vocabulary `item.tags` already measures (operand digits, regroup count and columns, zero
     pattern, presentation, context, steps). Every item is checked to fall inside its band's
     region — in `fill` and in `recheck`, so the whole bank is audited dimensionally — and no two
     bands of one skill set may declare the same region (that is what starved R1/R2's Hard bands).
     Easy / Medium / Hard / Advance stay the school's words on every screen; underneath they are
     labels over dimensions.
   - **Versioned rules, provenance on every item.** Editing a skill-set rule creates a new
     version; it never rewrites the row items were generated from. Every item records the
     skill-set version, generator, prompt and model that produced it, so "why did the engine give
     this child this question on that date" is always answerable from data.
   Gate additions: `engine load --check` refuses two bands with one region; `engine bank recheck`
   reports dimensional mismatches (must be 0); `select count(*) from item where skill_set_version
   is null` → 0.

   **Phase 1's finish line also includes the misconception analyst** (ADR 0012): a report of the
   most common *unclassified* wrong answers, per item and per rung, for a person to name. For any
   subject beyond arithmetic it is the only way the mistake vocabulary grows; it is built in W1 so
   W3's first real marks feed it from day one. Gate: `engine bank unclassified` runs and its
   output is recorded (empty until W3, which is the point — the instrument exists before the data).
5. **It runs as a workflow.** n8n F1 build-the-bank: trigger (a skill-set row changes, or a unit
   drops under 50) → `POST /bank/fill` → validator → items land `sample` until the set is
   ratified, then `approved` → any staff member can flag an item from the library, which retires
   it and feeds the eval. Exported to `n8n/workflows/f1-build-the-bank.json`; `n8n/lint.py`
   passes (no Code node, no prompt text, ids only). Gate: change one skill-set row and watch new
   items appear with nobody typing a command; the run visible as boxes in n8n.
6. **Cost and rate are known, and the cost is near zero.** Cost per accepted item and acceptance
   rate per unit, from `flow_run`, on the Skill Map screen. Gate: the query and its output, and the
   whole 64-unit bank's model spend under ₹50 — templates and their validation, nothing per item.
   Over that, the design has regressed to paying per question and the gate fails.

## Agreed with Nimish 2026-09-21 — built after the system is live on the server

Nimish: *"before developing this, I want whatever is there as a system to be live on the server."*
Nothing below starts until go-live (`deploy/go-live.sh`) has put today's system on a public link.

- **Multi-skill scoring (ADR 0023):** a question counts for every skill it uses — all of them when
  the child is right, the one whose part broke (named by the answer's mistake) when wrong. Each
  question's skills are read from the question itself, not copied from its rung.
- **Multi-skill questions** are skill sets of their own: two or three concepts combined in one
  question, as a complexity level — made by rows, filled by the engine like any other set.
- **Mixed-bag papers:** one paper drawing individual questions from two or three skill sets — a
  different thing from a multi-skill question.

## Parked — nothing here before W1's six gates pass

- **W3 reading engine on the 84 real sheets**: enter every paper, run every G2 and G3 scan, a
  person marks a sample → gold set → agreement %, a `validate_read` pass, the correction loop and
  per-child reading profiles (ADR 0007). Designed in `docs/superpowers/plans/2026-09-18-spine.md`
  chunks 3 and 6; that file's sequencing is superseded by this one, its designs stand.
- W2, W3, W4 as n8n flows; QR routing (`assess/mark.py` has the deskew/QR/crop scaffold, untested
  in this repo, with a placeholder reader); `/prescribe` `/assemble` `/render` endpoints.
- A second subject (ADR 0009): W1 gate 3 proves the rows-only path for maths; a second subject is
  W1 run again with its own master prompt, later.
- **One structured Assessment Specification** (external proposal §4) — a single named contract
  (subject, grade, skill, rung, signal, format, difficulty dimensions, count, purpose) that
  `/bank/fill`, prescribe and assemble all speak. Do it when W2 starts: that is when a second
  consumer of the shape appears.
- **The policy engine's objective as information gain** (external proposal §16) — "what evidence
  would most reduce uncertainty about this child?" rather than threshold rows. W4.
