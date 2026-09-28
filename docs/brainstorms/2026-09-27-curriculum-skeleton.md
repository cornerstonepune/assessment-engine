# Curriculum skeleton — brainstorm, to resume in a new session

27 September 2026 · status: **the crosswalk is built as data (28 Sep); the first sample is with Akanksha** · waiting on Nimish's answers to six questions (end of file)
Visual version: `docs/brainstorms/2026-09-27-curriculum-skeleton.html` (published: https://claude.ai/artifact/XY5Pvbwd4vjSTgj1K2R6mE)
Merged to main on 27 Sep (cornerstonepune/assessment-engine#73); follow-ups on branch `claude/sleepy-keller-j2ybm5`.

## How to resume

1. Read this file, then the HTML page above.
2. The imported data is in `docs/spine/sources/` (NCF-SE, NCERT, the school's units); the spine graph is `docs/spine/spine.json`;
   the clickable spine map is https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg.
3. Do not build anything until Nimish answers the six questions. He asked to brainstorm first: "first, we need a
   representation of how we think about it structurally, then we create the backend out of this very clearly".

## 28 Sep, later: built from the documents in hand, and the first sample is with Akanksha

Nimish: "no approver needs to actually write … have a proper prompt that we can align on … a sample which you can send
to Akanksha … start building the entire data structure … even if they are not from the Cambridge official website".

- **Built:** `docs/crosswalk/`, rows shaped like ADR 0041's tables. They hold:
  - 2,789 official statements, each with its page: NCF-SE, NCERT, and Cambridge Maths, English and Science read from
    other schools' copies;
  - 32 framework levels with ages;
  - 20 strands of one step per year of age;
  - 1,405 school objectives placed at their grade's age.
  `STATE.md` has the commands and their output.
- **The prompt to align on:** `docs/crosswalk/drafting-method.md`: one way of thinking in ten steps, a fixed word list,
  and the checks code runs.
- **The sample:** Grade 3 Number (age 8), 30 objectives drafted by the method. The first 20 rows went to Akanksha as a
  Google Sheet that asks only for Approve, Change or Reject.
- **What building showed:**
  - The school's Grade 3 already mixes Cambridge Stage 3 and Stage 4, so the age anchor fits the school.
  - Grade 4 repeats Grade 3's titles (78 of 89), which is why "what we say" has to carry the range for its age.

## 28 Sep, last: the crosswalk as tables (ADR 0041, proposed)

Nimish: "most of this is where you are saying that it's not been linked, so it is incomplete, right? … for a certain
learning objective: what does the NCF say, what does IGCSE say, and what are we going to say as a combination … That
essentially translates into the written skill outcome at a rubric level … for all the grades … If you have to convert
this into a proper set of tables such that this mapping becomes accurate, how will you want to do it?"

- **Answer:** yes, it is incomplete. No objective is linked to NCF-SE or Cambridge at the objective level, Cambridge
  is not imported, and no table records a signature. The design is `docs/adr/0041-…`. Page:
  https://claude.ai/artifact/KW1vV2p6c9Cxq6ThfTr2iR (source `docs/brainstorms/2026-09-28-crosswalk-tables.html`).
- **The design has five zones:**
  - what others say, imported word for word;
  - which grade reads which level;
  - what we say;
  - claims and signatures, where a model may propose and only an educator decides;
  - how we'll know: the skill outcome per strand, rubric descriptors per level, and evidence.
  Views answer the questions: `lo_crosswalk`, `framework_gap`, `readiness`.
- **Drive, searched read-only on 28 Sep:**
  - The only official Cambridge Primary framework is Physical Education (0069, Stages 1–6, file
    `1IG5pexvD-K9wHGv-ZSDJZn39GmbNeJlD`). Its objectives are banded by Stages 1–3 and 4–6, with codes like `123MW.01`.
  - Maths, English and Science frameworks are not there, and there is nothing for Lower Secondary or IGCSE.
    "IGCSE Curriculum.pdf" is another school's Grade 1 map.
  - The school's own syllabus documents cover G1–G4 only.
- **Scales already in use:**
  - the Hindi reading rubric (Beginning, Developing, Fluent, Expressive);
  - report cards (Outstanding, Desired, Improving out of 10, where 6/10 appears under two labels);
  - planning sheets (Level 1, 2, 3);
  - the registry's score out of 10 and yes / sometimes / no.
- **Five decisions for Nimish:** the Cambridge files and Grade n = Stage n; one rubric scale; rubrics per strand
  (recommended) or per objective; who signs each subject; pilot Grade 3 Maths now as data, or move the tables up in
  BUILD-ORDER.
- "Expensive" in his message is read as "expansive": the school's statement goes further than NCF-SE and Cambridge.

## 28 Sep, redesigned: the spine page reads as one thread (ADR 0038)

Nimish: "is there a way that you can design this html better such that its more easily understood and the
connections are untuitive - i am getting lost in the artifact".

- **Where:** the same link, https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg (version 3).
- **Thread view:** everything sits on the same five steps: why, what NCF-SE asks, in the grade, when, how we check.
  Clicking anything shows its thread through them, and each link is marked as NCF-SE or NCERT, the school's map,
  proposed or inferred.
- **A grade's year:** fortnights by subjects, with the units' own names.
- **The school day:** academic, studio, arts, sport, and circle and close, by grade.
- **Opens on:** Grade 3's addition and subtraction. It builds Thinking & reasoning, serves NCF-SE CG-1 and CG-4, and
  matches 5 of NCERT's Grade 3 outcomes. It is taught in fortnights 2–3 and checked by 2 engine skills (NUM.OPS.01,
  NUM.OPS.02).
- **Held by:** `goals/spine-readable.yaml`, whose five sentences are Nimish's words, each with its test in
  `packages/engine/tests/test_spine_page.py`.

What the rebuild found:
- **Routines in the plan.** 31 of the 637 items the plan places reach no capability: 30 of the school's units (Home
  Period, Science Week, the maths quiz every alternate week, Play-Based Learning (weekly) and more) and one NCERT
  outcome ("visits a language laboratory"). They are routines or
  inputs, not learning. The plan paces them like syllabus; a school timetable would give them fixed slots instead.
- **Arts units named as briefs.** 122 arts and social-science units in the school's map are named
  "• Title: … / • Focus: … / • Key Concepts: …". The page shows the title, and the focus and concepts on the unit's
  card. The map itself could carry the three as separate fields.
- **Dark-mode colours.** The last session's dark palette failed the colour-vision check (arts and studio ΔE 1.6 for
  deuteranopes). It is fixed by drawing the day in five parts; both themes pass.
- **"CATs" is still read as academics.** Nothing in this redesign depends on that reading beyond the day chart's
  "academic" block.

## 28 Sep, built: the Plan view inside the spine

Nimish: "don't keep on waiting for me ... Just give me the final output." Built on the reading below, with "CATs"
taken as academics.
- **Where:** the spine map, Plan view: https://claude.ai/artifact/KemZgBsaTfwSXbEg2ttcAg (deep link `#plan`).
  The map's explorer shows each school unit's and NCERT outcome's grade and fortnight.
- **Built by:** `python3 research/plan_build.py`, which writes `docs/spine/plan.json` (22/22 official quotes found
  on their page), then `python3 research/spine_page.py`.
- **Inputs:** the syllabus is the school's map for Grades 1–4 and NCERT for Grades 5–7. The design is
  `docs/spine/plan_design.json`: seven modes, the shape of an academic hour per stage, and weekly minutes. The design
  is a proposal.

What it shows at the defaults:
- Academic time is about 219 minutes a day in Grades 1–2, 165 in Grades 3–5 and 173 in Grades 6–7.
- NCERT outcomes go 37 → 72 → 89 from Grade 5 to 7, so hours per outcome fall from 13.1 to 4.6. The answer is how the
  hour is used (concept, level practice, customised check, a personal paper each fortnight) and projects that carry
  outcomes in groups.
- The Grade 1 map has 120 studio objectives for 47 hours of Discover.
- There are 16 fortnights (158 teaching days).
- The separate timetable page (28 Sep) is superseded by this view.

## 28 Sep, later: Nimish reframes the ask (outcome not yet agreed)

His words (trimmed):
- "I am not looking for the separate documents. I am looking for this in integration with the entire syllabus that we
  made ... And how can we break it down into fortnightly plans?"
- "Timetables are not sacrosanct; they are built with 80-90% conviction."
- "I'm not looking for the actual timetable per se ... The number of hours that are required and the schedule that we
  are suggesting: how does it work? ... the learning needs to happen the way we are designing the school": application-
  based learning; concepts explained in a very innovative, creative way; time for assessment; customised assessments;
  fluid class sizes by age and level; those slots every day; sports and arts time.
- "how the composition changes with increasing grades and how the CATs part increases. How can that CATs part still
  be powerful enough that ... we are able to achieve our objectives for the kind of children we want? Is the outcome
  clear here?"

Read as follows, pending his confirmation. "CATs" / "cat time" is probably "acads", meaning academics. The
outcome is one model inside the spine, not a separate page, running:
- from the outcomes, to the hours they need, to the fortnights they fall in;
- to the daily learning modes: concept, level practice, customised check, application, sport and arts, community;
- to how the mix of those modes shifts from Grade 1 to Grade 7.

Found in the school's Drive on 28 Sep, to build on:
- The Grade 1 Planning Sheet 2026 logs every activity's attendance by Level 1/2/3.
- The Cambridge Grade 1 maths plans split each lesson into Beginners, Intermediate and Advanced.
- The ICT plan for Grades 2–4 runs a shared 10-minute hook, 35 minutes of practice with one pathway per grade, and a
  shared 15-minute evaluation.
- A monthly Parent Day & Learning Showcase runs on portfolio stations.
- No Grade 1–4 timetable was found; the "Time Table" folder shows empty.

## 28 Sep: his answers, and the indicative timetable

- **Scope:** Grades 1–7 ("the first 7 standard curriculum is what I'm asking about").
- **"ITCS":** he meant IGCSE, that is, Cambridge. Below Grade 9, Cambridge means Cambridge Primary (Stages 1–6) and
  Lower Secondary (Stage 7).
- **"cat time":** he does not know what he meant. It is dropped; the morning block is called Core.
- **Calendar:** the usual Indian school calendar. "Two nature breaks" is read as the two daily breaks (snack and
  lunch); the year has a summer break and a Diwali break.
- **Timings:** 8:30 to 2:30, six hours. "You can create everything else."
- **Later:** an interface that generates the timetable from a set of conditions.

**Built now: the indicative timetable,** https://claude.ai/artifact/T46QvYnMgqyJW1hKktafYH. Source:
`docs/brainstorms/2026-09-28-indicative-timetable.html`. Its official numbers come from
`python3 research/timetable_data.py`, which found 22/22 quotes word for word on their cited page (NCF-SE Part A Chapter
4, NCERT, the graduate profile).

What it shows at the defaults (Monday to Friday, a 7-week summer break, a 3-week Diwali break, 12 weekday holidays,
NCF-SE's 20 test days and 20 event days):
- 158 teaching days × 285 minutes ≈ 751 hours a year, against NCF-SE's illustrative 955 (79%).
- With a 2-hour morning core, R2 and PE fall to about 62–63% of NCF-SE's hours in Grades 3–5, and Science and Social
  Science to about 66% in Grades 6–7.
- Alternate Saturday half-days (NCF-SE's own model) and 8 test days instead of 20 reach about 886 hours (93%).
- Grades 6–7 English and Social Science get about 3–4 hours per NCERT outcome.

The timetable is a proposal, not agreed. Cambridge is not counted, and the RTE Act's minimums were not verified
(India Code could not be reached).

## 27 Sep, after the merge: Nimish's next asks, and the objective put back to him

**Start here.** He asked for the objective to be agreed before any work: *"Is the objective clear? Just make sure that
we are first clear on the objective, and then only start working on it."*

His asks, in his words (trimmed):
- "check whether there are any elements of ITCS in terms of key skills and capabilities that we are missing out on".
  *"ITCS" is read as IGCSE, meaning Cambridge; he is to confirm.*
- "let's just do this till 7th standard … Map it in really good detail, and also map the elements that we would add
  extra as a school from the profile that we are intending to build for a child"
- "whether this makes mathematical sense if we had to start thinking about a concept taking a certain number of days.
  Based on the number of hours that we have, what should the school timings be then? Can we then work in a way where
  2 to 2.5 hours of cat time is there on a daily basis, and then conceptual application happens in the later half of
  the day?" *"cat time" is read as the morning's core concept time; he is to confirm.*
- "ensure that we are not just force-fitting in terms of words and that it actually makes sense"
- "Making someone mug from a textbook is very different than actually teaching children with application-based
  teaching … recalibrating their levels and making their classes fluid. They'll be doing a lot more projects."

**The objective, proposed and not yet agreed.** Answer one question with numbers anyone can check: *can Grades 1–7
teach every official outcome, plus the school's own, through application and projects, in the hours a school year
holds, and what school day follows from that?* It has four outputs, each feeding the next.

1. **The top holds.** Each of the eight capabilities is tested, not asserted. It must be observable in a child,
   distinct from the other seven, and fed by official outcomes in more than one subject. A capability that fails is
   merged, reworded, or declared a matter of school culture rather than curriculum. The gap check uses Cambridge's own
   named skills: the Cambridge learner attributes, and the "thinking and working scientifically / mathematically"
   strands. It uses official Cambridge text only, cited.
2. **The map, Grades 1–7.** Per subject per grade, every outcome carries its official code or the label
   "school-designed, from the graduate profile". The codes come from NCERT or NCF-SE, from Cambridge Primary Stages
   1–6, and from Cambridge Lower Secondary Stage 7. Outcomes are grouped into the units the school would teach; one
   project can carry several outcomes, across subjects.
3. **The time model.** Each unit's teaching days, taught by application, come from a stated assumption per kind of
   outcome, with a low and a high value. There is no per-row guess. The days are summed per subject per grade and set
   against the hours the year holds. The inputs are:
   - the school's calendar;
   - the RTE Act's minimum working days and instructional hours, quoted from the Act, not from memory;
   - NCF-SE 2023 Part A, Chapter 4, "Time Allocation" (contents page 112). Its day and week allocations for the
     Preparatory and Middle Stages are, in its own words, "illustrative", and the school decides.

   The output is, per grade, "fits" or "over by N hours", with the assumption that moves the answer most.
4. **The day.** From the totals: the school's timings, the morning core block (his 2–2.5 hours), the afternoon
   application block, and the weekly split per subject. These are tested, not asserted. If the day doesn't fit, the
   model shows what gives: fewer outcomes in depth, a longer day, or more outcomes per project.

Not in it: names, rooms or a real timetable, and any code, table, migration or screen. BUILD-ORDER is on step 1 of ten,
and the curriculum engine is not among the ten. Building it needs Nimish to insert it.

Put to him with the objective:
- A per-outcome time is an assumption until a pilot measures it. The model shows ranges and names the assumption that
  decides the answer; a single number would be a made-up number dressed as maths.
- Fluid levels bind the timetable. If children regroup by level in the core block, every section of a grade (or of two
  adjacent grades) needs that block at the same hour.
- Scope: Grades 1–7, or PG–7? The school's units run PG–G4, and NCF-FS covers ages 3–8.
- Question 2 below now reads: the map covers Grades 1–7, and the outcome cards (activities, conduct, materials, video)
  are written for one slice first.
- Needed from the school: the calendar (working days, holidays, exam days) and today's timings.

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

- `python3 research/spine_verify.py` (any directory; fetches NCERT's own PDFs, refuses a copy whose fingerprint differs)
  → NCF-SE 814/814 lines found in full, word for word; NCERT 729/729 outcomes found in full on their stated page.
  Held by `goals/spine-traceable.yaml` (`bin/engine done spine-traceable`) and run by CI on every PR.
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
