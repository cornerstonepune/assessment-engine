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
