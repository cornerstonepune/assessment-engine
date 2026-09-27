# Curriculum skeleton — brainstorm, to resume in a new session

27 September 2026 · status: **brainstorm, nothing built** · waiting on Nimish's answers to six questions (end of file)
Visual version: `docs/brainstorms/2026-09-27-curriculum-skeleton.html` (published: https://claude.ai/artifact/XY5Pvbwd4vjSTgj1K2R6mE)
Branch: `claude/sleepy-keller-j2ybm5` · PR: cornerstonepune/assessment-engine#73

## How to resume

1. Read this file, then the HTML page above.
2. The imported data is in `docs/spine/sources/` (NCF-SE, NCERT, the school's units); the spine graph is `docs/spine/spine.json`;
   the clickable spine map is https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg.
3. Do not build anything until Nimish answers the six questions. He asked to brainstorm first: "first, we need a
   representation of how we think about it structurally, then we create the backend out of this very clearly".

## What Nimish asked (26–27 Sep)

- The top of the spine is right: three words (capable, kind, unafraid) → eight capabilities → subjects.
- Below subjects, per subject per grade: child outcomes articulated properly, combining Cambridge and CBSE/NCERT.
  Up to Grade 6: the best of both. From Grade 7: CBSE is the minimum coverage, with Cambridge added where it is better.
- The mapping must be linear and deterministic, respect skill dependencies, and start tracking each child. Not too complex.
- A table structure (a database) that becomes the front end of a curriculum engine: for Science Grade 2, open the grade's
  outcomes, divided into fortnights, movable; a master prompt per subject drafts the curriculum outcome by outcome.
- Per outcome: the core articulation; a base level and an advanced level; 2–3 generated options (activities, games,
  events, real situations); how it is run in class, logistics, materials, what the educator observes; a video slot
  (generated, or made by the curriculum team). This card is the teachers' ready reckoner and the source of lesson plans.
  The timetable comes after.
- **Provenance, in his words:** "I want everything to be referenced to official documents … Nothing needs to be fabricated
  … run a validation agent as well, as part of the backend itself … For every learning objective … or the mark scheme …
  a reference attached to it. Tomorrow, anyone can trace back and say that we have not made something up." Turning an
  outcome into a skill for the child "is a different story".

## The proposal (for discussion, not agreed)

**One rule.** Every outcome rests on official lines, quoted word for word with document and page. Every clause of an
outcome, its base and its advanced level cites a code, or it is flagged and cannot be approved. Activities may be the
school's own design, and are labelled so; each "observe for" line cites a code.

**The chain.** 3 words → 8 capabilities → subject (agreed) → grade → **outcome (the unit of everything)** → base · advanced
→ activities (3 options, 1 chosen) → fortnight (one fixed order) → lesson (drawn from the card) → evidence → child
(not yet · base · advanced, computed from evidence by a counted rule).

**Which official text each grade rests on.**

| Grades | Backbone | Must also cover | May add, marked as added |
|---|---|---|---|
| 1–6 | Cambridge Primary objectives (Stages 1–6) | NCERT outcomes for the class | nothing outside the two |
| 7–8 | NCERT outcomes (the CBSE minimum) | NCF-SE Middle-stage competencies | Cambridge Lower Secondary (Stages 7–9) where stronger |
| 9–10 | CBSE curriculum for the year (board exam) | NCERT Secondary outcomes | Cambridge IGCSE, as enrichment, not examined |

**Tables.**

| Group | Table | Holds |
|---|---|---|
| Official, imported, never edited | `official_line` | source (NCF-SE, NCERT, CBSE, Cambridge Primary, Lower Secondary, IGCSE), document, edition, page, code, subject, grade or stage, verbatim text |
| The school's own, versioned, signed | `outcome` | subject, grade, strand, order in the grade, statement, base, advanced, status, version, signed_by |
| | `outcome_line` | outcome, clause → official_line (what it rests on, clause by clause) |
| | `outcome_needs` | outcome → outcome that must be taught first |
| | `outcome_capability` | outcome → capability (up to the three words) |
| | `activity` | outcome, kind (activity, game, event, real situation), steps, materials, logistics, minutes, observe_for (each with a code), provenance, option 1–3, chosen |
| | `media` | activity, kind, link, made_by (team, generated), reviewed |
| | `plan` | year, grade, subject, fortnight, outcome, order |
| | `timetable` | grade, subject, periods per week |
| | `mark_line` | question or rubric line → outcome + level (base, advanced) |
| The child (engine, exists) | `evidence` | child, mark_line or activity, blank · wrong · wrong with working · right, date, by whom (append-only) |
| | `child_outcome` | child, outcome, not yet · base · advanced (computed) |
| The machine | `prompt` (exists) | one master prompt per subject, versioned, with its score |
| | `check_log` | every validation: what, rule, pass or flag, signed_by, date |

**The validator, part of the backend.**
- *Code, every time:* every cited code exists; its text matches the official document on its page word for word; every
  official line for the grade is cited or marked "not taught" with a reason; nothing is planned before what it needs; the
  plan fits the timetable; every mark line names an outcome and a level.
- *A second model, flags only:* a different prompt from the drafting one. Does any clause say more than its cited lines? Is
  any clause uncited? It never approves.
- *A person signs:* the subject's curriculum lead clears each flag and signs. Nothing reaches an educator unsigned. Any mark
  in a child's record traces to the question, the outcome, the official line and its page.

**Who does what.** 1 import official lines (code) · 2 verify word for word (code) · 3 draft outcomes for a subject and grade
(model, master prompt) · 4 check citations and coverage, flag unsupported clauses (code + second model) · 5 edit 10–20% and
sign (curriculum team) · 6 draft three activities per outcome (model) · 7 choose, edit, add video (curriculum team) ·
8 order into fortnights, needs first, team can move (code, then team) · 9 fit to the timetable (code) · 10 lesson plans from
the chosen cards (code) · 11 teach, record evidence (educator) · 12 each child's status per outcome (code).

**The worked example** (Science, Grade 2, forces) is on the HTML page: it rests on Cambridge 2Pf.01, 2Pf.02, 2Pf.03
(Cambridge Primary Science 0097, Sept 2020 edition, PDF p.17) and NCF-SE C-7.2; needs 1Pf.01, 1Pf.02 (p.15); leads to 3Pf.01
(p.19). Its articulation and activities were written for the brainstorm and are marked generated.

## Verified facts (commands, not claims)

- `python3 research/spine_verify.py --ncf <NCF-SE text> --elementary <NCERT 2017 PDF> --secondary <NCERT 2019 PDF>`
  → NCF-SE 814/814 lines found word for word; NCERT 729/729 outcomes found on their stated page.
- Cambridge Primary Science 0097: 297/297 coded objectives parsed and re-found in the framework (scratchpad only, not yet in
  the repo); by stage 33, 43, 48, 59, 57, 57.
- NCERT sets no science outcome for Classes 1–2: "in classes III to V, it is introduced as a separate curricular area and in
  I and II, the related concerns are integrated with language and mathematics" (NCERT, Learning Outcomes at the Elementary
  Stage, 2017, EVS introduction, PDF p.93). For Grade 2 science, Cambridge is the only grade-level source.
- The school's Grade 2 science units (registry, band G2) teach Cambridge **Stage 3** lines: forcemeters 3Pf.01, gravity
  3Pf.02, friction 3Pf.03, shadows 3Ps.02, food chains 3Be.01, solids-liquids-gases 3Cm.01. A keyword match; a person should
  confirm.

## Not yet in the backend

The official Cambridge frameworks other than Primary Science (English, current Maths, Global Perspectives, Computing),
Cambridge Lower Secondary, IGCSE syllabuses, and the CBSE Classes 9–10 curriculum (downloaded during the council research,
not imported). The Cambridge Maths framework on disk uses an older code style (2Nc6), so it is probably a pre-2020
edition. The Science copy came from a school website hosting Cambridge's PDF; the official copy is behind the school's
Cambridge support-site login.

## Points put to Nimish

- IGCSE covers Grades 9–10 only; below that the Cambridge programmes are Cambridge Primary (Stages 1–6) and Cambridge Lower
  Secondary (Stages 7–9).
- "Linear" and "dependencies" are two things: dependencies form a web; the fortnight order is the one linear sequence,
  derived from that web and checked by code. "Deterministic" means a child's status is computed by a counted rule from
  evidence, never guessed by a model.
- Keep two levels (base, advanced); a third multiplies the educators' work.

## Six questions, waiting on Nimish

1. **Grade and stage.** Should Grade N teach Cambridge Stage N? Today Grade 2 science teaches Stage 3.
2. **A pilot slice.** Science and Maths in Grade 2, end to end first, before scaling?
3. **Two levels.** Base and advanced only?
4. **The fortnight.** The planning unit for every subject, languages and arts included? How many teaching fortnights a year?
5. **Who signs.** One curriculum lead per subject, whose sign-off is recorded?
6. **The documents.** The official Cambridge frameworks from the school's support-site login, and which CBSE year is the
   baseline?
