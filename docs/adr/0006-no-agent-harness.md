# ADR 0006 — No agent harness: single-shot prompts behind one adapter

Date: 2026-09-17. Status: accepted.

## Decision

Every model call in the engine is a single shot with a fixed JSON shape out, made through
`adapters/llm.py`: fetch the active `prompt` row, fill it, call, retry, validate against the row's
schema, write a `flow_run` row. There is no loop in which a model decides what to do next or
which tool to call. The loop is the workflow (n8n); the decisions are code (verifier, thresholds,
the six-state rules) or a person (Achal, Aseem, the coordinator).

The six prompts and their shapes:

| Prompt | In | Out |
|---|---|---|
| item_generate | the skill-set spec | items with answers and distractors |
| read_cells | a masked photo | one row per answer cell |
| read_page | a masked photo | a narrative observation |
| legacy_extract | an old paper | answers, for the import |
| word_context | numbers and a format | one sentence a child reads |
| parent_note | the map and a template | a note a parent reads |

## Why

- Nothing in the twelve nodes needs a model to choose among tools at run time.
- CLAUDE.md rule 3 says n8n never thinks; a harness would put a thinking loop inside the engine
  instead, which is the same defect in a different place.
- A harness adds a dependency, a debugging surface and a cost that cannot be explained to a
  coordinator reading a failed run. Six single calls can.
- "Agentic prompts" in the founder's sense — one prompt does a whole job — is satisfied: the
  generation prompt writes an entire bank from a spec.

## Rejected

- **Claude Agent SDK / Tool Runner / Managed Agents.** Right for open-ended tasks with tools;
  wrong for six fixed-shape calls boxed in by verification and human confirmation.
- **A workflow engine inside Python (LangGraph and kin).** Duplicates n8n, which already owns
  sequencing and waits.

## Revisit trigger

A node appears where the model must pick between tools at run time, or a prompt's output must be
iterated on by the model itself before a person sees it. Neither exists in N1–N12.

## Consequences

Provider is a one-file change: the pilot calls Gemini over REST; production on Claude replaces
`_call` with the Anthropic SDK and nothing else moves. Every prompt keeps its eval (rule 7).

## Amended 2026-10-26: an educator's sample is the pattern (goals/gen_from_a_sample.yaml)

Nimish: "the ability for the system to then generate a certain number of questions of that pattern." A seventh shape:

| Prompt | In | Out |
|---|---|---|
| english_generate | one English sample an educator chose, its level, rule, kind and mistakes | questions of the same pattern |

Still one call, no loop: the model writes, then code decides. Every question it returns passes the same checks as an
educator's own sample (`english_check.py`) or is thrown away, never shown or stored, and the educator is told how many
and why. What passes is a draft: it says "made from your sample", can be removed one by one, and its level waits for
approval, so no paper draws it before a person approves the level. The prompt is a row, inactive until `engine eval
english_generate` scores it on a fixed set (`supabase/seed/english_generate_gold.json`) and the score is in
DECISIONS-LOG.md (rule 7). A Maths sample calls no model (ADR 0005): code measures it, makes more of its case where the
level holds it, and keeps it as a sample only where it does not. Rejected: letting the model's question reach a paper
on its own checks alone (a person approves the level first), and a model reading a Maths sample (code can).

Amended 2026-10-27 (goals/genfix_rubric_in_reply.yaml): the passage and the rubric of a question made from a sample
are the sample's, carried over by code; the model is neither sent them nor asked for them. v1 was sent the sample with
its `rubric_code` and told to answer "in the same fields as the sample", so it returned one its schema forbids, and
the first eval ended with no score (run 40469097359). Rejected: adding `rubric_code` to the schema. A question a person
reads is complete only with its rubric, but one of the sample's pattern is read against the sample's rubric, chosen
by the educator and already checked; a model's choice would be a second answer to a settled question, to be checked
back to the same value.
