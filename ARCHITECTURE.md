# Architecture — the engine, and exactly where n8n sits

This file settles one question: **what runs what.** It reconciles the twelve-node workflow agreed
with Aseem and Achal (`docs/sources/assessment-workflow-v1.md`) with the engine internals
(`docs/sources/assessment-engine-spec-v0.1.md`). Where those two disagree, the workflow wins.
Where this file and `SPEC.md` disagree, this file wins on *who runs it* and SPEC wins on *what it
does*.

## 1. The shape in one line

**The engine is the thing. n8n is the wiring.** Everything that has to be *correct* — arithmetic,
item generation, marking, diagnosis, the child graph, the next prescription — is deterministic
Python behind an HTTP API. n8n knows *when* to call it and *who to tell*. It holds no logic, no
prompt, no rule, no threshold.

Read it as four parts with hard edges:

| Part | Owns | Where |
|---|---|---|
| **Database** | every fact, once | Supabase Postgres, `ap-south-1` |
| **Engine** | all computation and all judgment calls | `packages/engine`, Python, HTTP |
| **n8n** | triggers, sequencing, waits, Drive and WhatsApp I/O, retries, run logs | `n8n/workflows/*.json` |
| **App** | the six screens a human touches | `apps/web`, Next.js |

## 2. Where n8n is — node by node

The workflow's twelve nodes, and who actually executes each. This is the table to argue with, not
the prose.

| Node | What happens | n8n's part | The real work |
|---|---|---|---|
| **N1** Skill sets & ladder | Neha and Achal write the sets; Aseem ratifies | — | engine `load`, seed files, a human |
| **N2** Question bank | generate items for a skill set × difficulty | **trigger + schedule** — fire on template change, nightly top-up when a pool runs low | engine `POST /bank/fill` |
| **N3** Roster & seed state | import the historical papers as candidates | **trigger** on a folder, then hand to the confirm queue | engine `legacy import` (CLI), then humans confirm |
| **N4** Week declaration | teacher says what was taught | **listens** — receives the voice note or form, calls the engine, posts the five lines back for confirmation | engine structures it; **Achal decides** |
| **N5** Prescribe per child | who gets which skill set at which difficulty | **sequence** — after N4 confirms | engine `POST /prescribe` |
| **N6** Build packs | assemble, render, pack in handout order | **sequence + Drive upload** | engine `POST /assemble` → `/render` |
| **N7** Teacher approves | pack goes out, teacher taps or replies | **WhatsApp send + wait-for-reply** — this is n8n's single most valuable job | **Achal decides**; an edit re-runs N5/N6 for that child |
| **N8** Capture | photos land, QR resolves them | **Drive folder watch** | engine `POST /ingest` — QR, never a model |
| **N9** Mark & diagnose | read digits, mark by lookup, tag misconceptions | **sequence + notify** "N items to confirm" | engine `POST /mark` and `/read`; **Achal confirms** the doubtful |
| **N10** Evidence & state | append evidence, rebuild the graph | **nightly schedule** + on confirm | engine `POST /graph/rebuild` |
| **N11** Cards & home sheet | class card, home pack, parent note | **sequence + send**, after Friday's capture | engine `POST /cards` → `/home`; **Achal confirms**, which releases them |
| **N12** Reports & planning | monthly parent reports, regrouping, "not ready" flags | **monthly schedule** | engine `POST /reports`; **coordinator approves** |

Count the column: n8n fires a trigger, waits for a human, moves a file, sends a message, logs the
run. Eleven of twelve nodes do their actual work inside the engine or inside a person's head.

## 3. What must never live in n8n

Straight from spec v0.1 §7, and binding:

> Prompts · item templates and constraint logic · the picker · the renderer · the answer-key and
> misconception tables · the marking rules.

Add to that list: thresholds, blueprints, the six-state rules, the difficulty bands. All of them
are rows in Postgres, fetched at runtime.

**The test:** if you can only find out what the system does by opening the n8n UI, something has
been put in the wrong place. Every rule should be visible in a migration, a seed file, or a tested
Python function — diffable, reviewable, and covered by an eval where a model is involved.

If a workflow needs logic, the fix is an engine endpoint, never a Code node.

## 4. Why n8n at all, then

Three jobs it genuinely does better than code we would otherwise write:

1. **Wait for a human without holding a process open.** N7 sends a pack on WhatsApp and waits —
   possibly for hours, possibly forever. That wait is the hardest thing on this list to write well,
   and it is the heart of "everything approved by the teacher."
2. **Watch the outside world.** A Drive folder gains files at unpredictable times. n8n watches it
   so the engine does not have to run a poller it also has to supervise.
3. **Be legible to a coordinator.** When Friday's pack does not arrive, someone who does not read
   Python can open the run, see which step failed, and re-run it.

The cost of those three is that workflows must be exported to `n8n/workflows/*.json` and reviewed
in pull requests like code. Editing in the n8n UI without exporting is a defect.

## 5. The engine's surface

n8n's entire vocabulary. Nothing else is callable.

```
POST /bank/fill        {skill_set, difficulty, count}   -> items generated, validated, approved
POST /declare          {class, week, transcript}        -> structured declaration for confirmation
POST /prescribe        {class, week, kind}              -> one prescription per child + spares
POST /assemble         {prescription_ids}               -> sheets from unexposed approved items
POST /render           {sheet_ids}                      -> PDFs, answer keys, cell geometry
POST /ingest           {drive_file}                     -> QR -> sheet -> child, or needs_rephoto
POST /mark             {capture_id}                     -> item_results, misconception tags
POST /read             {capture_id}                     -> narrative_observation (whole page)
POST /commit           {result_ids, confirmed_by}       -> evidence_events (append-only)
POST /graph/rebuild    {class?}                          -> child_skill_state, six states
POST /cards            {class, week}                    -> class card
POST /home             {class, week}                    -> home sheets + parent notes
POST /reports          {class, month}                   -> parent reports in the Kabir format
```

Every one is idempotent and writes a `flow_run` row: what ran, how long, what it cost, what failed.

## 6. A week as a sequence of calls

```
Wed eve   teacher voice note ──n8n──> /declare ──n8n──> five lines back ──> Achal confirms
Thu 07    n8n ──> /prescribe(practice) ──> /assemble ──> /render ──> Drive
          n8n ──> WhatsApp pack + key ──> waits ──> Achal taps approve ──> print
Thu 13    Drive watch ──> /ingest ──> /mark + /read ──> n8n notifies "3 to confirm"
          Achal confirms ──> /commit ──> /graph/rebuild
Fri 07    same as Thursday, kind=assessment — now knowing Thursday's result
Fri eve   n8n ──> /cards ──> /home ──> Achal confirms ──> home sheets released,
                                       next week's prescription seeded
Monthly   n8n ──> /reports ──> coordinator approves per child
```

The loop closes at Friday evening: N11's output is what N5 reads next Thursday.

## 7. The item generation engine

The point of N2 is that it works for **any** topic. Give it a skill set and a difficulty and it
produces a question list — addition today, multiplication and fractions next, without anyone
editing Python to add a topic. Three things multiply together to make that true.

### 7.1 Three layers, and which is code

| Layer | What it is | Code or data | Who writes it |
|---|---|---|---|
| **Operation family** | the arithmetic of one operation: how to sample operands under a constraint, and what number each mistake produces | **code**, ~120 lines per family | engineer, once per family |
| **Format** | the shape a question takes on paper — column sum, horizontal, missing number, balance scale, number line, number wall, partition scaffold, find-the-mistake, word problem, explain, sort-into-table… | **code**, 17 exist and are topic-agnostic | engineer, reused forever |
| **Skill-set spec** | which sets exist, their operand rules at Easy/Medium/Hard/Advance, which formats apply, which misconceptions | **data** — rows, authored | Neha and Achal (N1), Aseem ratifies |

A format is not tied to an operation. "Missing number" is `□ + 7 = 12` and `□ × 7 = 42` and
`□ + ¼ = ¾` — the same shape asking a different question. That reuse is what makes a new topic
cheap.

### 7.2 What a skill set looks like as data

Multiplication, the topic Aseem's own reports keep flagging. Nothing here is code:

```yaml
skill_set: MUL.4
  name:        2-digit × 1-digit with carrying
  skill_code:  NUM.OPS.03
  can_do:      "multiplies a 2-digit number by a single digit, carrying between partial products"
  formats:     [column_grid, bare_sum, missing_number, find_mistake, word_1step]
  difficulty:
    Easy:    { a: {digits: 2, tens: 1..4}, b: {range: 2..3}, carries: 0 }
    Medium:  { a: {digits: 2},             b: {range: 2..5}, carries: 1 }
    Hard:    { a: {digits: 2},             b: {range: 6..9}, carries: 1..2 }
    Advance: { a: {digits: 3},             b: {range: 6..9}, carries: 2..3 }
  misconceptions: [M_MULT_CONCAT, M_PARTIAL_NOT_ADDED, M_CARRY_ADDED_BEFORE_MULT, M_TABLE_FACT]
```

`M_MULT_CONCAT` is the error Aseem diagnosed by hand: partial products computed correctly, then
written side by side instead of added — `56 × 3 = 1518` rather than 168. As a predictor it is four
lines of arithmetic, and once written, every multiplication item can be marked against it.

### 7.3 The generation run, step by step

This is N2 as a workflow, which is how you have been describing it. Each step is one thing:

```
  1  read the skill-set spec                      data      (Postgres)
  2  for each difficulty × format slot:
  3    sample operands under the rules            Python    exact, constraint-checked
  4    compute the correct answer                 Python    never a model
  5    compute what each misconception produces   Python    the diagnostic table
  6    if the format needs a sentence:            prompt    word problem, find-the-mistake framing
         the model receives the numbers and       ← numbers are an input, never an output
         may not change them
  7    validate                                   Python    recompute the arithmetic independently,
                                                            confirm the item exercises the rule it
                                                            claims, reject duplicates, check reading
                                                            load and forbidden vocabulary
  8    derive the case tags                       Python    taxonomy §12, from the parameters
  9    store as approved                          data      the template was trusted upstream
```

Step 6 is the only place a model appears, and it is boxed in from both sides: the numbers are
chosen before it runs, and step 7 re-checks everything after. A model that hallucinates writes a
bad *sentence*, which a validator catches — it can never produce a wrong *answer*.

### 7.4 What it costs to add a topic

| Adding… | Costs |
|---|---|
| a new skill set inside an existing operation (another addition set) | **rows only** |
| a new difficulty band, or re-tuning operand rules | **rows only** |
| a new format (say, an area model) | one Python function, then available to every topic |
| a new operation family (multiplication, fractions) | one sampler + its predictors, ~120 lines, once |

Fractions will also need a renderer that can draw a fraction — that is format work, not topic work.

### 7.5 Where this stands today

Honest position: **the formats are general, the topic layer is not.** `items.py` holds 17 formats
that already work across operations. But `ladder.py` and `blueprints.py` are Python dictionaries
covering addition and subtraction only, so a new topic today means editing code — which rule 1
forbids.

The work to close it:
1. Move rungs, skill sets, difficulty bands and blueprints out of Python into seeded rows.
2. Make the sampler read operand rules from those rows instead of from a function signature.
3. Add the multiplication family — sampler and predictors, `M_MULT_CONCAT` first.

Until step 1 lands, "adding a topic is data" is a design claim, not a fact. The test that proves
it: **add a multiplication skill set using only rows and the editing screen, and get printable
questions out.** If any Python changes, the design failed.

## 8. Built, and not

| | |
|---|---|
| **Built** | the database (30 tables, RLS); `engine load`; item generation, blueprints, rendering with QR and cell geometry; the misconception predictors; case tagging; 53 tests |
| **Next** | N3 — import the 37 real papers as candidates for confirmation, producing each child's starting graph |
| **Then** | N8/N9 on real photos, measured against Aseem's marking; the six-state graph; N5 prescription |
| **n8n arrives at** | N7 — the first point where something must wait for a person. Before that, a CLI run by a person is the honest tool, and n8n would be overhead |

Nothing in the first two rows needs n8n. That is not an accident: the orchestration layer is worth
installing when there is something to orchestrate that runs without us.
