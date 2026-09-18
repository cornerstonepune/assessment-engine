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
| **W1** | Build the bank (N1–N2) | any skill on the map, its learning objective, a difficulty | hundreds of verified questions per skill × difficulty, for any topic, by rows only | **← we are here. 0 of 6 gates pass** |
| W2 | Assemble and print (N5–N7) | each child's prescription | per-child papers with QR, spares, key; the teacher approves | engine functions exist and are tested; not a workflow yet |
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

1. **Every rung has a ratifiable spec.** 16 of 16 rungs on the ladder have a `skill_set` row: name,
   learning objective, philosophy lines, formats, misconceptions, and for each of Easy, Medium,
   Hard, Advance a rule in words plus a checkable rule. Drafted by the engine for Neha and Achal to
   correct, ratified by Aseem (N1). Gate: `select count(*) from rung r where not exists (select 1
   from skill_set s where s.rung_code = r.code)` → `0`, and every row `ratified`.
2. **Every skill × difficulty unit is rich, produced by code from the spec.** At least 50 approved
   items in each of the 64 units (16 rungs × 4 difficulties — ~50 per skill per difficulty is the
   number agreed with the school in the workflow document), enumerated by `engine bank fill` from
   the rule in the skill-set row, answers and distractors computed, no model call for the
   arithmetic. Gate: `engine bank coverage` prints the 16 × 4 table with no cell under 50, and
   `flow_run` shows the fill's model spend for the + and − units was zero.
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
