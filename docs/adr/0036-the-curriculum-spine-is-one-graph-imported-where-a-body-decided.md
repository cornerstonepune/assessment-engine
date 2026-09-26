# 0036 — The curriculum spine is one graph: imported where a body has decided, generated where it has not, every generated link flagged

Date: 2026-09-26
Goal: none — a design artefact (`docs/spine/spine.json` and the page rendered from it); the organ that holds it
as rows starts with its own goal file when its turn comes after the ten steps (CLAUDE.md rule 12)
Status: **proposed** — needs Nimish's ratification of the shape; the generated links need the curriculum team's pass.
Source: `research/spine_build.py` (the assembly and its checks), `research/spine_council/` (the seats' crosswalks and
the brief they read), `docs/spine/sources/` (what was imported and from where).

## Context

Nimish asked for the whole spine, three words down to grade-wise competencies, "as an HTML architecture which can be
clicked through like a decision tree, with each step breaking down and showing the connect … like a neuron, a mental
map, and that's what becomes our foundation for what we develop from there." The layers already existed in five
places: the graduate profile (words, capabilities), the council's draft (behaviours), NCF-SE 2023 (curricular goals
and competencies per subject per stage), NCERT's two learning-outcome documents (per class, 1–10), and the school's
own maps in `supabase/seed/registry.json` (units, skills, rungs). Nothing joined them.

## Decision

1. **One graph.** Nodes for every layer and edges for every connection, in one file, with a layer on every node and a
   provenance on every edge: `imported` (a body decided: NCF-SE, NCERT), `school` (the school's own maps), `council`
   (the four-seat review of the behaviours), `survey` (the platform survey), or `seat:<subject>` (generated).
2. **Imported where a body has decided.** Competencies are NCF-SE's, by subject and stage, with their own codes; grade
   outcomes are NCERT's, by class; neither is paraphrased. Where the school has its own decided map (units, skills,
   the skill-to-NCF links it already carries, the engine's rungs), that is imported too.
3. **Generated where it has not.** The links no body publishes, competency to capability, competency to grade,
   outcome to competency, unit to competency, are proposed by one subject seat each from the texts, checked by
   code (ids exist, grades sit inside the row's stage, every row covered or a reason given), and carried as
   proposals: the page marks them "generated" and the curriculum team accepts, edits or rejects them. Nimish's
   rule: the system generates, the team edits ten to twenty percent.
4. **The page is rendered from the graph**, never edited by hand: a map of the layers, a node view that shows what a
   node comes from and leads to, a tree from the three words, a by-grade view, and search. `research/spine_page.py`.
5. **Known holes are written on the graph, not around it**: a unit or outcome with no competency carries a `why`;
   the seats' notes ship in the file and on the page.

## Rejected

| Alternative | Where proposed | Why not |
|---|---|---|
| A spreadsheet per subject | the usual way | no cross-links between subjects and capabilities; drifts from the sources within a term |
| Generate the competencies with a model | the first reading of "generate everything" | NCF-SE and NCERT have decided them; a model paraphrasing a board's competency is a defect (ADR 0010: code, or here a body, enumerates; a model writes language only where nobody has) |
| A graph database for the spine | the Student OS document | ADR 0035: Postgres closure table when the organ exists; until then a file a program checks |
| A strict tree | the words "decision tree" | a competency feeds several capabilities and a unit builds several skills; the spine is a directed graph read as a tree from any node |
| Hand-map the crosswalks first | caution | 1,700-odd links; the team's time goes to accepting or editing a proposal, not to a blank sheet |

## Consequences

- Prompt version 2 for behaviours, the observation Scribe and the Holistic Progress Card all key on node ids from this
  graph; they change only when a source changes.
- Two parsing faults found by the foundational seat were fixed at source (the Positive Learning Habits rows were
  filed under the wrong domain; two footnotes were glued into texts); the NCERT elementary outcomes fold sub-points
  into their parent line, so a few Class 1–2 rows fuse several outcomes. Both are recorded on the page's notes.
- Which language is R1, R2 and R3 for Cornerstone, and whether Hindi and Marathi outcomes come from Maharashtra's
  SCERT, are the founders' decisions; the seats mapped English to R1 and said so.
