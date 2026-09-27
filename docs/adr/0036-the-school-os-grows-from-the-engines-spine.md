# 0036 — The school operating system grows from the engine's spine; the three architecture documents are read through it

Date: 2026-09-26
Goal: none — a design proposal that builds nothing; each organ it proposes starts with its own goal file when
its turn comes after W4 (CLAUDE.md rule 12)
Status: **proposed** — needs Nimish's ratification. Until then, BUILD-ORDER and ADRs 0001–0034 bind as before.
Source: `docs/school-os-council-2026-09-26.md` (the council's synthesis), whose research is in
`research/research_notes/School operating system council/`.

## Context

Nimish brought three documents to a council on the whole school operating system:

- the Cornerstone Blueprint v2 (`docs/sources/cornerstone-blueprint-v2.html`);
- the Student OS architecture and Jev specification (`docs/sources/student-os-architecture-and-jev.pdf`);
- the SchoolOS PRD (`docs/sources/schoolos-prd-lean-architecture.md`).

They disagree with each other and, in places, with decisions this repository has already measured. A later
session reading `docs/sources/` could otherwise act on a rejected alternative: LangGraph, Neo4j, Temporal,
a routing proxy, or Jev.

## Decision

**Blueprint v2 stays the house reference, with five amendments.** The other two documents are background.

1. **No second workflow runtime.** A human wait is a row in a queue table, visible on a screen. n8n fires
   triggers and schedules; the engine does the logic (ADRs 0003, 0006). This amends Blueprint v2's
   "LangGraph-TS front-runner".
2. **No autonomous agent at run time.** Observation extraction is one fixed-shape call. Curriculum co-editing
   is a tool the curriculum team drives, not an agent acting on records. This amends Blueprint v2's two
   agents.
3. **A decision registry, with Jev as its first provider for text-in decisions.** The registry generalises
   what exists: prompt rows, the gold set and measured overturn rates. Jev serves the decisions that are "read
   this text, choose from these options" at volume: routing an observation to a child, competency and stream;
   naming the mistake behind a wrong answer that code cannot reproduce; tagging generated questions and lessons
   to competencies; checking generated pedagogy against constraints; checking each report line against its
   evidence; a second net for safeguarding flags, routed to a person. Four lines hold: Jev never reads
   handwriting (it reads no images, ADR 0019 stands); code keeps every exact job; each decision starts in
   shadow and acts alone only after beating our own gold set; Jev receives ids, never names, under a
   data-processing contract. *Revised 2026-09-26 after Nimish's pushback; the first draft said "no Jev", on
   the 2026-09-21 research that measured it against today's assessment prompts alone.*
4. **Counted mastery rules stay the truth.** Ratings with uncertainty sit beside them from W4 on. Bayesian
   knowledge tracing runs in shadow only; deep knowledge tracing is never used at this scale.
5. **Gate by decision class** (the synthesis, section 6):
   - *Checkable by code and reversible* settles alone, with blind spot-checks, once its accuracy is measured
     on our children.
   - *A judgement, or anything that writes to the record,* is decided by a person.
   - *Anything a parent sees* is decided by two people.
   - *Emotion, body and "risk" inference* is never built.

   This generalises ADR 0029's reasoning from one kind of answer to every decision.

Build order is unchanged: `BUILD-ORDER.md` holds. The synthesis proposes the order of new organs only for after
W4 closes.

## Rejected

| Alternative | Proposed in | Why rejected |
|---|---|---|
| Neo4j or Memgraph for the curriculum and child graphs | PRD; Student OS | 244 skills and 849 milestones fit a Postgres closure table; joins do not cross databases |
| Temporal, or LangGraph plus Temporal | PRD | Operational weight for one founder; waits are rows |
| LangGraph-TS or the OpenAI Agents SDK as the flow core | Blueprint v2; Student OS | No step needs a model to choose its path; ADR 0006's revisit trigger has not fired |
| Triage when the model's confidence is below 85%, or when a result is ±2.5σ from the child's average | PRD | Vendor confidence is not a probability: the reader's "90+" was right 33 times in 42 on the answers people typed (ADR 0032). With a young child's handful of results, ±2.5σ flags sudden understanding and ignores a child who stays stuck. |
| pyBKT as the mastery engine | PRD | Stable parameters need 250–500 students per skill; a counted rule is what a teacher can read |
| A four-tier routing proxy with a semantic cache | PRD | One adapter per service with pinned model ids is simpler and keeps every accuracy measurement valid |
| Exponential decay of behaviour tags, half-life 90 days | PRD | No behaviour score should exist to decay; notes are dated, and a pattern needs recurrence across adults |
| Self-hosted Faster-Whisper on a GPU | PRD | A GPU to run; weaker on Indian languages than hosted Indic models |
| ArUco corners, DataMatrix and a Typst renderer | PRD | Phone scan apps crop corners; alignment to the printed PDF works without them, and the renderer exists |
| Jev as the "nervous system": the source of truth or the orchestrator | Student OS | Jev is a provider behind the decision registry, not the store or the runtime; the Student OS document itself says it should be neither |

## Revisit when

- a step needs a model to choose between tools at run time;
- the registry reaches a size a Postgres closure table cannot serve in under a second;
- Jev or a similar decision model reads images and beats the gold set with no more silently-wrong answers, at which point the handwriting line above is revisited;
- more than about 500 children give a skill enough responses to fit knowledge-tracing parameters.

## Consequences

`docs/sources/` now holds the three documents as background. Where they disagree with this repository, this ADR
says which way and why. Nothing is built from them until Nimish ratifies the synthesis and W4 closes.
