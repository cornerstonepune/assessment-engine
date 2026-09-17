# Cornerstone Assessment Engine — design spec

Status: approved shape (approach A), awaiting Nimish's read-through before the implementation plan.
Scope: Grades 1–4 whole-number addition and subtraction, built first for Grade 2–3. Everything else
in the Learning OS (voice capture, planning, reports) is out of scope here but the data model is
the shared one, so nothing built here is thrown away when those arrive.

## 1. What this is for

A teacher photographs a pile of completed worksheets. By the next morning the system knows, per
child and per skill, what is secure, what is a repeating mistake (and which one), and what to give
next — and has drafted the next worksheet, the home practice, and the parent note. The teacher
confirms; she never types.

Five outputs, each one the test of whether the build is working:

| Output | Who | Test |
|---|---|---|
| Print pack in handout order | coordinator | one stack, no sorting |
| Confirm queue after capture | teacher | under 2 minutes per class |
| Monday card per rung: secure / reteach group with the named mistake / ready to move up | teacher | she changes a Monday decision because of it |
| Child growth: skill state over time | teacher, coordinator, later parent | four real assessments show a trend |
| Next worksheet per child, chosen from the graph, with the reason | teacher hands out; may override | every child with enough evidence gets a sheet and a stated rule; overrides are rare and recorded |
| Home sheet + parent note | teacher approves, parent receives | note is plain, concrete, no alarm |

## 2. The shape — one organism, not many programs

```
                 ┌──────────── n8n (nerves) ───────────┐
                 │ triggers · waits · Drive I/O · notify │
                 └───┬───────────────┬─────────────────┘
                     │ HTTP          │ HTTP
   Next.js (skin) ──►│  engine (muscle, Python)          │
   six screens       │  generate · render · ingest       │
   reads DB directly │  mark · graph · cli               │
        │            └───────┬───────────────┬──────────┘
        │                    │ SQL            │ adapters
        ▼                    ▼                ▼
   ┌────────────── Supabase Postgres (bloodstream) ─────────────┐   Drive · Claude vision · notify
   │ Ring A truth  │ Ring B derived │ pii schema │ prompts · runs │
   └────────────────────────────────────────────────────────────┘
```

Rules that keep it one organism:

- **One database.** Every part reads and writes the same Postgres. "How is this child doing" is one
  join. `tenant_id` on every table and row-level security from the first migration: a second
  school is a row, not a rewrite.
- **Code where correctness is needed, a model where judgment is needed.** Arithmetic, marking,
  misconception lookup, graph rebuild: code, deterministic, tested. Reading handwriting, reading a
  whole page for behaviour, writing a word-problem context, drafting a parent note: Claude, behind
  one adapter, with a versioned prompt and an eval set.
- **n8n orchestrates, never thinks.** It holds triggers, credentials, sequencing, human-approval
  waits, Drive and notification I/O, retries. No prompt, no blueprint, no marking rule lives in a
  node. If logic appears in a Code node, it moves to the engine.
- **Nothing structural is hard-coded.** Bands, rungs, levels, blueprints, misconceptions, prompts,
  thresholds are rows. Adding Grade 5 or a new rung is an insert, not a deploy.
- **Ring B is disposable.** Derived state is rebuilt from Ring A nightly and can be truncated at any
  time. If a rebuild changes a child's state, that is a bug in the rule or a fact in the evidence,
  never a lost row.

## 3. The skill model — three layers, no fourth taxonomy

Three documents describe "what a child can do" at different grains. They are reconciled as layers
of one model, not competing vocabularies.

| Layer | Source | Example | Used for |
|---|---|---|---|
| **Skill** | the registry (`window.CSMAP`, 244 skills, ratified by the school) | `NUM.OPS.02` Subtraction | joining to everything else in the Learning OS: report lines, activities, objectives |
| **Rung** | the R1–R14 ladder (spec v0.1 §1) — a stage on the strand | `R6` 2-digit subtraction with exchange | which difficulty a child is given, blueprints, the child's position, the Monday card |
| **Case tags** | the team's *Addition & Subtraction Assessment Skill Taxonomy* §12 matrix | `{op:SUB, d1:2, d2:2, presentation:VERTICAL, regrouping:SINGLE, regroup_columns:[ONES], zero_pattern:NONE, answer_digit_change:SAME, unknown:NONE, reasoning:DIRECT, context:BARE}` | item generation and selection; guaranteeing no case is silently missing; item statistics per case |

Case tags are **derived by code from the generator's parameters**, never typed. A blueprint slot
asks for a rung, a signal (Foundational / Conceptual / Procedural / Application / Stretch) and
optionally tag constraints; the picker fills it.

### 3.1 Why three layers and not two

The rung ladder and the taxonomy answer different questions, and collapsing them loses one of the
answers. A rung says **where a child is on the journey** — it is the unit a teacher reasons in,
the unit a difficulty is chosen within, and the unit of the Monday card. A case tag says **which exact case was
tested** — and the taxonomy's own definition is that a case is distinct "whenever a child can make
a different kind of mistake".

Checking the taxonomy's §13 progression against the ladder confirms the split rather than
contradicting it:

| §13 stage | Lands on |
|---|---|
| 1 direct, no regrouping · 4 single regrouping · 5 multiple/cascading · 6 zeros | R1–R4 · R5/R6 · R9 · R10 — **rungs** |
| 8 three or more addends · 11 efficient mental · 12 word problems · 13 error diagnosis | R12 · R7/R13 · R8/R14 · X2 — **rungs** |
| 2 horizontal vs vertical · 3 unequal digit lengths · 7 answer-size changes | **not stages at all — dimensions**, which is why they are tags |
| 9 missing number/digit · 10 equality/inverse/checking | split: whole-number unknowns sit at R7, missing *digits* at R13 |

Stages 2, 3 and 7 are the proof. They are not places on a journey — a child meets horizontal
presentation at every rung — so a two-layer model has nowhere to put them, and they disappear.
They are precisely the cases the coverage audit found missing.

### 3.2 What the taxonomy adds that the ladder alone missed

Run against today's blueprints, the dimensions immediately surfaced two holes:

- **Presentation.** R5, R6, R9, R10 and R12 are generated in columns only. The same arithmetic
  written horizontally is never assessed above Grade 1, so horizontal-to-vertical conversion —
  a documented error type (§11) with its own misconception (`M007` column misalignment) — cannot
  be detected at any rung where it matters.
- **Operand length.** R4, R5, R6, R10 and R12 use equal-length operands only. `342 + 5`, where
  the 5 must be aligned under the ones, is never assessed outside R9.

Neither needs new generator code: `sample_add` / `sample_sub` already take separate digit counts
per operand, and `col()` / `bare()` already choose layout. The blueprints simply never asked.
Both are fixed by adding slots, which is a seed change, not a code change — the test of §4's rule.

The taxonomy also adds a word-problem dimension the ladder flattens. R8 says "one- and two-step
word problems"; §10.1 distinguishes eleven structures (result / change / start unknown × join /
separate, part-part-whole whole or part unknown, compare difference / larger / smaller unknown).
"Had some, gave away 13, now 24" is far harder than "had 37, gave away 13" on identical numbers.
That becomes the `word_structure` dimension, not eleven new rungs.

### 3.3 The dimensions

Eighteen: the seventeen from the taxonomy's §12 master tagging matrix, plus `word_structure`.
Each is a row in `case_dimension` with its allowed values. The taxonomy's own instruction is
followed exactly — *"do not encode every possible combination as a separate hard-coded topic
name; store these dimensions as tags, then generate or select question sets by combinations of
tags"* — so the named case codes (A01–A72 and the rest) are **not** imported as rows. They are
combinations, and combinations are derived.

What *is* stored is the target: `coverage_target` holds, per rung, which dimension values must
appear before that rung counts as assessed. The coverage report is then one query — for each
rung, which targets have no approved item, and which have items but no evidence. That is the
answer to "what do we claim to teach but never actually check", and it is the reason the
dimensions are a table and not a JSON blob.

### 3.4 Misconceptions the taxonomy adds

§11's error list maps mostly onto predictors that already exist (`M_NOCARRY`, `M_CARRY_SKIP`,
`M_SMALL_FROM_LARGE`, `M_NO_DECREMENT`, `M_ZERO_LENDER`, `M_ZERO_NOT_NINE`,
`M_EQUALS_MEANS_ANSWER`). Five are genuinely new and are seeded with their detectability:

| Code | Error | Detectable by |
|---|---|---|
| `M_H2V_SHIFT` | Horizontal-to-vertical conversion shifts the shorter number left | `working` |
| `M_ALIGN_LEFT` | Aligns unequal-length operands from the left, not the ones | `answer_lookup` |
| `M_CARRY_ALWAYS_1` | Assumes a carry is always 1; fails when three addends make a column sum ≥ 20 | `answer_lookup` |
| `M_ZERO_DROPPED` | Drops a leading, trailing or internal zero when writing the answer | `answer_lookup` |
| `M_MISSING_DIGIT_LOCAL` | Finds a missing digit that works in its own column but not across the carry | `working` |

`M_ALIGN_LEFT`, `M_CARRY_ALWAYS_1` and `M_ZERO_DROPPED` are computable from the operands, so they
join the predictor table and are tagged automatically like the rest.

Registry gaps the ladder exposes (3-digit and across-zero subtraction have no G3 milestone; G4 has
no content ladder) are handled by `rung.milestone_id` being nullable and a coverage report, not by
editing the registry from this repo. Registry changes go to Akanksha through the Skill Map Review.

**Misconceptions** are one table from three sources: the prototype's answer-lookup predictors
(`M_NOCARRY`, `M_SMALL_FROM_LARGE`, …), the Adaptive Subtraction spec's M001–M010 (conceptual),
and the taxonomy §11 error list. Each row says how it is detectable — `answer_lookup` (a wrong
number matches the predicted wrong number), `working` (visible in the working box), `explanation`
(only from what the child says), `teacher`. Only `answer_lookup` rows are tagged automatically.

## 4. Tables

Postgres, schema `public` unless noted. Every table: `id`, `tenant_id`, `created_at`, `updated_at`;
RLS on. Names are singular. JSON only where the shape is genuinely per-row (geometry, tags,
responses).

**Ring A — source of truth (append/approve; never edited by a batch job)**

| Table | Holds | Written by |
|---|---|---|
| `tenant` | one row per school | migration |
| `skill` | registry skill: id (`NUM.OPS.01`), domain, strand, name, description, source | loader from CSMAP |
| `milestone` | registry band descriptor per skill: band, descriptor, scale | loader |
| `rung` | ladder stage: id (`R5`), band, order, descriptor, skill_ids[], milestone_id (nullable) | seed |
| `level_rule` | (band, level) → rung_ids[]; foundational and probe rungs | seed |
| `blueprint` | (band, level) → ordered slots [{label, generator, args, rung, signal, tags?}] | seed; editable by coordinator |
| `misconception` | code, op, name, description, repair_hint, detectable_by, source, external_ref | seed; grows from `unclassified` reviews |
| `item` | one generated question: template, rung_id, skill_ids[], signal, format, stem, spec, responses[] (rid, kind, answer, cells, options, misconceptions{code→wrong}, tolerance, rubric), tags, source, status, times_used, p_correct | engine generate |
| `sheet_template` | one assembled worksheet design: band, level, child_id (the seed — sheets are per child, not per class), week, batch_id, blueprint_id, item_ids[], key (answers + cell geometry in mm), html_path, source (`generated` \| `legacy`) | engine assemble / legacy CLI |
| `sheet_instance` | one physical page set: id = the QR code (`CS…`), sheet_template_id, child_id (nullable until named), print_status, pdf_path, printed_at | engine render; coordinator (naming, print status) |
| `prescription` | why this child gets this sheet this week: child_id, week, strand, level, rung_ids[], rule_fired, misconception_targets[], sheet_instance_id, override_by, override_reason | engine prescribe; teacher override |
| `child` | roll_no, band, section, active — **no name here** | roster loader |
| `pii.child` | first_name, last_name, home_languages[]; separate schema, separate role, access logged | roster loader |
| `capture` | one incoming file: drive_file_id, path, pages, qr_read, sheet_instance_id (nullable), status (`new` \| `resolved` \| `needs_rephoto` \| `processed` \| `error`), error | engine ingest |
| `item_result` | one response on one capture: item_id, rid, raw_read, read_confidence, status (`correct` \| `wrong` \| `blank` \| `unreadable` \| `needs_teacher`), misconception_codes[], working_shown, state (`candidate` \| `confirmed` \| `rejected`), confirmed_by/at | engine mark; teacher confirm |
| `narrative_observation` | one per capture: text, signals {self_correction, guessed, fatigue, method_pattern}, prompt_version | engine read (Channel B) |
| `evidence_event` | the shared log: child_id, skill_id, rung_id, correct, misconception_codes[], channel (`item`), item_result_id, observed_at, stored_at, confirmed_by | engine on confirm — **append-only** |
| `home_sheet` | child_id, week, target_skill_ids[], item_ids[], pdf_path | engine |
| `parent_note` | child_id, week, body, prompt_version, approved_by, sent_at, channel | engine draft; teacher approve |
| `prompt` | purpose, version, text, model, json_schema, active | seed; new version = new row |
| `gold` | hand-marked truth for prompt evals: capture_id, item_id, rid, truth | Aseem/teacher via CLI |
| `flow_run` | every n8n or CLI run: flow, trigger, started/finished, status, error, tokens, cost | n8n + engine |
| `access_log` | who read which child's pii rows, when | trigger on `pii` |

**Ring B — derived (TRUNCATE-able; rebuilt nightly from confirmed evidence only)**

| Table | Holds |
|---|---|
| `child_skill_state` | child_id, skill_set, rung_id, difficulty (E/M/H/A), state (`not_enough_yet` \| `patterned` \| `emerging` \| `practising` \| `secure` \| `stretch_ready`), n_events, n_correct, repeating_misconception, last_seen, computed_at |
| `class_card` | (section, week, rung) → secure[], reteach{misconception→children[]}, move_up[]; the Monday card, drafted |
| `item_stat` | item_id → n, p_correct, flagged_mislevelled |

Thresholds (minimum events for a state, the 80% / 50% next-sheet rule, 21-day exposure, the
0.2 / 0.95 item flags, auto-confirm confidence) live in a `threshold` table, not in code.

## 5. Flows

Eight steps, and which part does each:

| # | Step | Trigger | Does the work | Human |
|---|---|---|---|---|
| 1 | Load registry + ladder | CLI, once and on registry publish | engine `load` | — |
| 1b | Fill the item bank for a rung; a named reviewer approves before anything can print | n8n **F1**, on demand per rung | engine `generate` → `validate` | **reviewer approves each item, once** |
| 2 | Assemble one sheet per child from approved items only, seeded by the child so no two are alike | n8n **F2** schedule or button | engine `assemble` → `render` | coordinator reviews the library |
| 3 | Print & name | button | Next.js writes `sheet_instance` | coordinator |
| 4 | Capture | n8n **F2** Drive trigger | engine `ingest` | teacher drops photos |
| 5 | Mark (A) + read (B) | F2 continues | engine `mark`, `read` | — |
| 6 | Confirm | F2 notifies | Next.js queue → engine `commit` | teacher, < 2 min |
| 7 | Rebuild graph → prescribe next sheet per child → draft cards | n8n **F3** nightly | engine `graph`, `prescribe`, `cards` | — |
| 8 | Home sheet + parent note from the same prescription | F3 continues | engine `home` | teacher approves |

**The next-sheet rule** (every number is a `threshold` row, not code). For each child and strand,
after the nightly rebuild:

- at-band rung ≥ 80 % correct across the last two sheets and no misconception repeated → **step up
  a difficulty**, or to the next rung if already at Advance;
- < 50 %, or the same misconception on two sheets → **step down a difficulty**, and the blueprint's
  procedural slots are swapped for a targeted repair mini-set (3–4 items) on that misconception;
- otherwise → **hold the difficulty** and keep practising;
- any skill set still `not_enough_yet` → the seed grouping's difficulty, never a guess, and
  over-sample it next week.

The picker fills the prescribed blueprint with items this child has not seen in 21 days. The
result is one `prescription` row per child per week, naming the rule that fired, and one
`sheet_instance` with its own QR. A teacher override is a new `prescription` row with a reason
and an `evidence_event` on channel `teacher_override`, so the graph learns from it.

With four assessments per child, the rungs those papers covered will carry 4–12 events each —
enough for a state and a prescription on day one. Rungs no paper touched stay `not_enough_yet`
and get the default; the first generated sheets close that gap.

### 5.1 The item bank — the template is the unit of trust

Generators do not feed worksheets directly; they fill a bank. But **items are not reviewed one by
one — the template is.** Aseem approves a template once: its operand rules, its misconception
table, its format. Every item the template then produces is validated by code (arithmetic
recomputed independently, constraints actually exercised, no duplicate, reading load within the
grade's cap, forbidden vocabulary absent) and lands as `approved`.

That is what makes the bank affordable. A thousand questions per cell is a parameter, not a
person's weekend. A per-item review queue would put a human between the generator and every sheet
forever, and there is no version of that which scales to four grades.

Target is ~50 unused items per skill set × difficulty per active child — topped up nightly when a
pool runs low. Procedural items are effectively unlimited. Items accumulate statistics: after
roughly thirty results, anything answered correctly by under 20% or over 95% at its own rung is
flagged as mis-levelled and retires.

What a person *does* review: the template when it is new (N1/N2), the pack before it prints (N7,
under three minutes, at pack level), and the doubtful reads after capture (N9, under two minutes).

### 5.2 Difficulty: Easy / Medium / Hard / Advance

The school's own vocabulary, authored by Neha and Achal per skill set, ratified by Aseem. Not
bound to grade level — Aseem: *"push the top as far as they go; focus on those below the
objective."*

Rung and difficulty are different axes and both survive:

- **Rung** — which concept stage. `R5`, two-digit addition with one regrouping.
- **Difficulty** — how hard within that stage. E/M/H/A, set by operand rules the teachers write.

A prescription therefore reads *"Kabir: R5 at Hard this week"*. The earlier `L− / L0 / L+` labels
were a third vocabulary for the same idea and are retired; September's *Level A / Level B* was
the same shorthand and retires with them. One name per concept.

### 5.3 Every child gets different questions at the same level

A sheet is assembled per child, not per class. The blueprint fixes what the sheet *is* — which
rungs, which signals, how many of each — and the picker fills each slot from approved items using
a seed derived from the child. Ten children at Level A get ten different papers of identical
difficulty. Copying from a neighbour gains nothing; the teacher holds one key that covers the lot.

Two constraints on the picker, both of which need the bank to exist:
- **Within a class**, draw without replacement where the bank allows, so no two children in the
  same room get the same question.
- **Across weeks**, exclude any item that child has seen in the last 21 days.

### 5.4 The week, as agreed with Aseem and Achal

The canonical description is the twelve-node workflow (`docs/sources/assessment-workflow-v1.md`,
and the page at claude.ai/artifact/7vLHpTKuLV1jpsvEduea8e). This spec implements it; where the two
disagree, the workflow wins.

| | | Node |
|---|---|---|
| Mon–Wed | teach; no system interaction | — |
| **Wed evening** | **teacher declares what was taught** — a voice note or five lines. This is what starts the week; nothing runs on a clock alone. | N4 |
| Thu 7am | prescribe per child → build the practice pack → teacher approves in under 3 min → print | N5 N6 N7 |
| Thu | guided practice · photograph the pile · marked within minutes | N8 N9 N10 |
| Fri 7am | prescribe again, now knowing Thursday → assessment pack → approve → print | N5 N6 N7 |
| Fri | assessment · photograph | N8 N9 N10 |
| **Fri evening** | class card + **home sheet**, built from what Thursday and Friday showed; teacher confirms, which releases the home sheets *and* seeds next week | N11 |
| Monthly | parent reports in the Kabir format; revisit sets; regrouping; "not ready" flags | N12 |

Two packs a week, different blueprints: Thursday is practice, Friday is assessment. The home
sheet is built **after** both, never alongside them — it exists to repair what the week exposed.

Achal's whole week: one voice note, two taps, two photo sessions, one card confirm, about ten
minutes of queue.

### 5.5 What the teacher actually carries

One folder, printed from one PDF: **named sheets in roll order** (name pre-printed, QR ties sheet
to child and to the exact items), then **three or four unnamed spares per difficulty** with no
level printed on them, then **one teacher key page** — what each child got and why in a line, and
which spare to hand a child who finishes early.

She hands them out top to bottom. She never matches a child to a level, never marks, and never
sees a difficulty label in front of a child.

### 5.6 The three flows

**F1 build-the-bank** (on template change; nightly top-up when a pool runs low): generators
produce items, the model writes only the sentence around numbers the generator already chose, the
validator recomputes everything, rows land `approved`. No human in the loop — the template was
approved once, upstream.

**F2 assemble-and-print** (Thu 7am and Fri 7am, after the declaration): read prescriptions →
assemble per child from unexposed approved items → render → pack in handout order with spares and
the key → WhatsApp to the teacher → she taps approve or replies with an edit in words, which
re-runs that child and comes back. Open: is silence approval? Proposed yes for practice, no for
assessment.

**F3 read-and-respond** (the loop that closes): Drive trigger on the capture folder → POST
`/ingest` → QR resolves the sheet to a child → `/mark` and `/read` in parallel → anything
uncertain to the confirm queue → teacher confirms → `evidence_event` rows. Then nightly:
`/graph/rebuild` → `/prescribe` → `/cards` → `/home`, which produces next week's three outputs
per child, each chosen from that child's own graph: **the worksheet** (practice at their level),
**the assessment** (what to test next), and **the home sheet** (extra reps on exactly the pattern
that keeps recurring, with the parent note). Unreadable QR → `needs_rephoto`, visible in Capture.

F3 is where the loop closes: its output is the prescription F2 reads next week.

**Legacy import** (every assessment done so far, and any future non-QR paper) is an engine CLI,
not an n8n flow: `engine legacy import assessments/G3/2026-09-03_week1_add-sub`. It reads the
folder layout in `~/cornerstone/assessments/README.md` (one folder per paper, one PDF per child,
`roster.csv` per grade). It is run a handful of times by a person, so it does not earn a workflow.

The matrix is a row in `config`, e.g. `{bands:[G2,G3], strands:[ADD,SUB], difficulties:[E,M,H,A],
variants:2}` — the school edits it, not the code.

## 6. How a worksheet is parsed

**Generated sheet (QR + fiducials):**

1. Load image; find the four black 7 mm corner squares by contour (area, aspect, fill); pick the
   one nearest each corner.
2. Perspective-warp to the canonical page: 8 px/mm, 1680 × 2376. Every later step works in
   millimetres, so a phone photo and a flatbed scan are the same thing from here on.
3. Read the QR in its known top-right window → `sheet_instance.id` → child, template, answer key,
   cell geometry. Nothing about the child is on the page except the printed name.
4. For every response cell in `key.geometry`, crop with a 0.6 mm inset (the printed box line is
   excluded). Digit cells: one Claude vision call **per page** carrying all that page's crops in
   order with a strict JSON schema `[{item, rid, k, digit: "0–9" | "", confidence}]`. Tick boxes:
   ink ratio, no model. Working boxes: ink ratio → `none / partial / full`, no model. Text boxes:
   ink present → `needs_teacher` with the rubric shown; no auto-mark ever.
5. Mark by lookup, no model: join digits → compare with the key (tolerance for estimates) →
   `correct`; else look the number up in the response's `misconceptions {code → wrong}` → codes,
   or `unclassified`; empty → `blank`; low confidence → `unreadable`. Blank, wrong and
   wrong-with-working stay three different signals.
6. One whole-page Claude call (Channel B) → `narrative_observation`: self-correction, blank vs
   guessed, fatigue across items, a method repeating. Never overrides step 5.
7. Everything lands as `candidate`. The confirm queue shows only `unreadable`, `needs_teacher`,
   `unclassified`, and any cell under the auto-confirm confidence threshold. Confirmed rows become
   `evidence_event`s.

**Legacy sheet (no markers — every assessment done so far):**

1. The assessment paper is entered once as a `sheet_template(source=legacy)`: item number,
   printed question, answer, **rung** (the CLI suggests one from the question's shape; the person
   entering confirms), and — for bare column sums — the misconception predictions computed from
   the printed operands by the same predictor code. The rung is what lets a legacy result feed
   the graph and the next-sheet rule exactly like a generated one.
2. Each scan → one whole-page Claude call with the `legacy_extract` prompt → JSON per item
   `{n, question_as_printed, child_answer, attempted, working_summary, self_corrected}`; matched to
   the template by item number and by the printed question text (mismatch → queue).
3. Steps 5–7 above, unchanged. Results carry `source=legacy` so the graph can weight them.

**Olympiad paper (SOF IMO)**: MCQ; imported as one legacy template with option answers; only
items that are addition/subtraction get skill and rung tags, the rest carry the score only.

## 7. What information comes out

| Grain | Fields |
|---|---|
| per response | status, digits read, confidence, misconception codes or `unclassified`, working shown |
| per sheet | narrative + four signals, pages, resolution path (QR / manual / legacy) |
| per child × rung | one of six states, n events, n correct, the repeating misconception, last seen, source mix |
| per child over time | the trajectory: state and evidence per assessment date (the four points) |
| per child, next week | the prescribed sheet (level, rungs, targeted misconception) and the rule that chose it |
| per class × rung | secure list, reteach groups keyed by misconception, ready-for-L+ list |
| per item | n used, p_correct, mis-levelled flag |
| per prompt version | precision / recall against `gold` |

## 8. Prompts

Five, each a row in `prompt` with a JSON schema, fetched by purpose at runtime, never inline:

| purpose | input | output |
|---|---|---|
| `read_cells` | page crops in order | digits + confidence |
| `read_page` | whole page | narrative + signals |
| `legacy_extract` | whole page + expected item count | per-item answers and working |
| `word_context` | numbers, rung descriptor verbatim, grade word cap, forbidden words ("borrow"), approved names | stem only; numbers may not change |
| `parent_note` | child's flagged misconception rows + repair hints | 4–6 plain sentences, Cornerstone voice |

Every prompt has an eval: `gold` rows for the reading prompts (hand-marked cells and pages),
a fixed input set with human-graded outputs for the writing prompts. A prompt version ships only
with its eval score in `DECISIONS-LOG.md`.

## 9. Interfaces

Six screens, from the approved mockup, Next.js, server-rendered, reading Supabase directly; actions
call the engine.

| Screen | Shows | Actions |
|---|---|---|
| Skill Map | registry skills for NUM with their rungs, coverage (which rungs have items, which have evidence) | none — registry edits go through the Skill Map Review |
| Worksheets | this week's prescribed sheet per child, grouped by section, each with its reason; the class sets beneath; every sheet with a real preview; filter by band/strand/level/week | **Prescribe & generate this week**; Customize one sheet's blueprint before print lock; Override a child's prescription (reason required) |
| Assessments | every `sheet_instance` and where it is | name a spare; mark printed / with teacher |
| Capture | Drive-sync feed: what came in, what resolved, what needs a re-photo; the confirm queue | confirm / correct / reject a candidate |
| Child Growth | one child: state per rung, trajectory across assessments, narratives, and the next prescribed sheet with why | none |
| Home Assignment | this week's home sheet and the parent note draft | approve, send |

Roles from the platform doc apply: teacher sees own classes; coordinator all; parent (later) only
confirmed, narrative outputs. Brand: Lime wash / Basalt / Terracotta; Young Serif, Atkinson
Hyperlegible, JetBrains Mono for every id, date and number.

## 10. Repo

```
assessment-engine/
  CLAUDE.md  SPEC.md  STATE.md  HANDOFF.md  DECISIONS-LOG.md
  docs/adr/            one file per rejected alternative
  docs/sources/        team documents this design incorporates (taxonomy, adaptive spec text)
  supabase/            config, migrations/, seed/ (registry json, rungs, levels, blueprints, misconceptions, prompts)
  packages/engine/     Python 3.12 · assess/ (moved from the prototype) · api/ (FastAPI) · adapters/ (drive, vision, notify) · cli.py · tests/
  apps/web/            Next.js · six routes · one Supabase client
  n8n/                 docker-compose.yml · workflows/F1.json F2.json F3.json (exported, reviewed like code)
  data/                gitignored: scans, renders, print packs
```

Languages: Python for the engine because the validated code is Python and image work belongs
there; TypeScript for the app because Supabase's grain is TypeScript; SQL for everything
structural. No third language.

## 11. Build order and gates

| Phase | Ships | Gate (machine-checkable) |
|---|---|---|
| 0 | repo, migrations, loaders, seeds, engine moved in with its tests green | `engine load` twice = zero diff; 37 NUM skills, 16 rungs, 14+ misconceptions, 3 prompts present |
| 1 | legacy import of the uploaded G2/G3 assessments → confirm queue → evidence → graph v0 → Child Growth | every scan resolved to a child and an assessment; ≥ 95 % agreement with Aseem's marking on 3 sheets; a real child shows ≥ 2 points |
| 2 | prescribe per child from the Phase 1 graph → generate → library with previews → per-instance QR → print pack in roll order; F1 | every G2/G3 child with ≥ 2 confirmed assessments has a prescription naming its rule; children below the evidence threshold get the band default; a new rung added by rows only changes output |
| 3 | ingest → mark → read → confirm on new-format sheets; F2, F3 | roundtrip on real photos ≥ 95 % on closed items; confirm queue timed < 2 min per class |
| 4 | Monday card, home sheet, parent note | teacher confirms the card changed a decision; note approved without edits twice |

Phase 1 comes before generation on purpose: it produces the first real trajectory from data that
already exists, and it is the first real test of vision reading.

## 12. Verification

- Engine: pytest — generators (constraints hold, no duplicate operands across variants), predictors
  (each named wrong answer reproduces), marking rules (three signals never collapse), the
  roundtrip as a test with a fixed seed. Coverage ≥ 80 % on changed code.
- Loader idempotence; fake-band test (add a band and a rung by rows, generate, no code change).
- Prompt evals against `gold`; a version is rejected below the previous score.
- App: Playwright screenshot per screen at desktop and 400 px.
- Every claim of "works" is a command and its output in `STATE.md`.

## 13. Privacy

Children's names live only in `pii.child` and on the printed page. Scans and photos stay in Drive
and the gitignored `data/`; never in the repo, never in a prompt log. Prompts receive crops and
pages, not names. `access_log` records every read of `pii`. Consent text for item results and
work photos is Nimish's to obtain before the first non-founder class run (open decision 1).

## 14. Open decisions — Nimish's, not technical

1. Consent text and purpose register covering item results and work photos.
2. Parent-note channel for v1: WhatsApp, email, or none until the loop is trusted.
3. Who approves generated word-problem items before print — Aseem, Neha, or the grade teacher.
4. Whether the SOF IMO papers count toward the trajectory or are stored for reference only.
5. n8n hosting after the pilot: this machine (Docker) is fine to start; a Mumbai VPS keeps
   children's photos on infrastructure the school controls.

## 15. Deliberately not building now

Guessing for a child without evidence (a child whose rungs are all `not_enough_yet` gets the band
default, not an inferred level), multiplication and fractions (blueprints only, when the ladder
exists), WhatsApp inbound
photos, the adaptive tutor engine (its misconception codes are reused, the engine is not built),
Kreeyo integration (roster is a CSV until Kreeyo has an export), any second store.
