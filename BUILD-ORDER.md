# BUILD-ORDER — one workflow at a time, each perfected before the next

This file is the operating system for this repository. Every session reads it first, says which
workflow and which gate it is on, and does not touch a later workflow until every gate of the
current one passes in `STATE.md`. Nimish set this on 2026-09-19 after three sessions drifted
across the map and left every part incomplete. Nothing here is a suggestion.

## The four workflows, in the order they are built

The names are `ARCHITECTURE.md` §6.1's; the nodes are `docs/sources/assessment-workflow-v1.md`'s.
Each workflow is built *as a workflow*: an n8n flow (trigger → engine endpoints → validator agent
→ human gate → notify), prompts as rows with evals, thin engine functions behind endpoints, and a
screen where a person acts. "Built" means all of that, not the Python alone.

| # | Workflow | In | Out | Status |
|---|---|---|---|---|
| **W1** | Build the bank (N1–N2) | any skill on the map, its learning objective, a difficulty | hundreds of verified questions per skill × difficulty, for any topic, by rows only | **done: `engine goal w1-build-the-bank` → 10/10 scenarios, 5/5 criteria (2026-09-20)** |
| W2 | Assemble and print (N5–N7) | each child's prescription | per-child papers with QR, spares, key; the teacher approves | **← we are here. `goals/w2-assemble-and-print.yaml` written 2026-09-20, 0 of 9 scenarios met** |
| W3 | Read and graph (N8–N10) | scanned or photographed papers | marked answers, mistake patterns, the child's skill graph | a first reader has run on 10 of the 84 real sheets; nothing measured; not a workflow |
| W4 | Close the loop (N11–N12 → N5) | the graph | next paper, home sheet, parent note, per child | not started |

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
