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

### 6.1 The same twelve nodes as four workflows

This is the shape Nimish holds the system in, and it is the shape n8n will show:

| Workflow | Nodes | In | Out |
|---|---|---|---|
| **W1 build the bank** | N1–N2 | topic, objective, skill, philosophy, difficulty rule — as rows | verified items, `approved`; a staff flag retires one |
| **W2 assemble and print** | N5–N7 | each child's prescription | per-child sheets with QR, spares, teacher key; teacher approves |
| **W3 read and graph** | N8–N10 | photos | evidence, the child's skill graph in six states |
| **W4 close the loop** | N11–N12 → N5 | the graph | next practice sheet, next assessment, home sheet, parent note — each pointed at what that child got wrong |

W4's output is W2's input the following week. The whole engine exists so a child spends the next
week on the pattern that keeps recurring, not on the class average.

## 7. The item generation engine (W1)

The requirement, in Nimish's words: *given a topic, a learning objective, a skill and the
philosophy of the assessment — through a prompt — an agent creates the bank. No code is written
to make questions or to attach them to the skill map. Any staff member can give feedback on what
came out.* That is what is built. Decision and evidence: ADR 0005.

### 7.1 A prompt generates, code verifies, staff retire

| Step | Who | What |
|---|---|---|
| 1 | **data** | the skill-set spec, authored in a form by Neha and Achal: topic · learning objective · registry skill · the difficulty rule in words at Easy/Medium/Hard/Advance · the philosophy lines ("say exchange, never borrow", "one idea per item", "contexts a Pune 7-year-old knows") · allowed formats · the misconception list with descriptions |
| 2 | **prompt** | `item_generate`, a versioned `prompt` row, receives the spec and returns N items as JSON: operands, answer, stem, and for every listed misconception the exact wrong answer that mistake produces |
| 3 | **code** | the verifier: recompute the answer · check the rule (digit counts, regroup count, zeros, sign) · compare each misconception claim to a predictor where one exists · reject duplicates and forbidden words |
| 4 | **code** | derive the taxonomy §12 case tags from operands and format |
| 5 | **data** | passing items land `approved` — the template was trusted upstream, per the workflow. Failures are discarded and counted in `flow_run`; a rising failure rate is the signal to re-version the prompt |
| 6 | **human** | any staff member, from the library screen: thumbs-down and one line. The item is retired and never printed again; the flag joins the prompt's eval set (rule 7) |

The model is the author. Code is the examiner. Neither does the other's job, and the answer key
is never a model's last word.

### 7.2 Measured

One run, 2026-09-17, Hard subtraction, twenty items, everything in step 1 given as plain text
(`research/2026-09-17-prompt-generation-spike.md`): the rule was met on 20/20, arithmetic was
right on all twenty, 77/77 misconception distractors matched the code predictors, and the three
items the verifier rejected were a JSON field filled wrongly on missing-number items — caught,
not printed. The word problems read like a teacher wrote them.

### 7.3 What stays code, and why

| Code | Why it cannot be a prompt |
|---|---|
| the verifier | it is the guarantee. A generic arithmetic check is a few lines and works for any operation; a rule check (regroup count) is ~10 lines per operation, written once |
| the 27 misconception predictors | they make the diagnostic table *exact*. Without one, the model's claim is accepted and checked later at marking: a child's wrong answer that matches nothing goes to the confirm queue the teacher already works |
| the 17 formats and the renderer | paper shapes, topic-agnostic; a new shape (area model, fraction bar) is one function, then every topic has it |
| `items.py` / `blueprints.py` samplers | **demoted, not deleted.** They are the fallback when the model is unavailable and the oracle the prompt is evaluated against. They are no longer how a topic is added |

### 7.4 What it costs to add a topic

| Adding… | Costs |
|---|---|
| a skill set, any topic, any difficulty | **rows**, in a form |
| a misconception | **a row** with a description; the model computes its wrong answer. A predictor is optional and makes it exact |
| a difficulty rule the verifier cannot check yet ("exactly one carry" for ×) | ~10 lines in the verifier, once per operation |
| a format | one renderer function, once |

### 7.5 Where this stands today

Steps 1–6 exist as engine code behind a CLI (`engine bank fill | recheck | flag | sheet`,
`engine eval item_generate`); the HTTP wrapper and the library screen do not. The skill-set spec
is a `skill_set` row (four seeded as drafts for Neha and Achal), the school philosophy is a
`config` row, the prompt is a `prompt` row, and a staff flag is an `item_feedback` row whose
trigger retires the item. `ladder.py` and `blueprints.py` are still Python dictionaries for the
deterministic generators (a rule-1 violation, unchanged) — the prompt path does not read them.

Measured on the first real fill (STATE.md): every item the model returned had correct numbers;
what stopped the run was the free tier's rate limit, not the engine. The verifier's first version
was too strict in two ways and stored nothing — both are now regression tests.

The proof still to run: **Neha adds a multiplication skill set through the form and printable
questions come out, every answer verified by code.** Python may change only inside the verifier,
only to add a rule check; if anything else changes, the design failed.

## 8. Built, and not

| | |
|---|---|
| **Built** | the database (32 tables, RLS); `engine load`; **W1 as engine code** — skill-set rows, the `item_generate` prompt, the Gemini adapter, the verifier, `engine bank fill/recheck/flag/sheet`; the deterministic generators and blueprints; rendering with QR and cell geometry; the misconception predictors; case tagging; 98 tests |
| **Next** | N3 — import the 37 real papers as candidates for confirmation, producing each child's starting graph |
| **Then** | N8/N9 on real photos, measured against Aseem's marking; the six-state graph; N5 prescription |
| **n8n arrives at** | N7 — the first point where something must wait for a person. Before that, a CLI run by a person is the honest tool, and n8n would be overhead |

Nothing in the first two rows needs n8n. That is not an accident: the orchestration layer is worth
installing when there is something to orchestrate that runs without us.
