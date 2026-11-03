# The school OS map: one structure, every module, what is built and what is not

2026-11-03 · a map, not a decision · read with ADR 0098 (the Teacher OS, K2 first), ADR 0036 (the school OS grows from
this spine), ADR 0041 (the crosswalk), ADR 0084 (the curriculum is tables) and `docs/school-os-council-2026-09-26.md`.

Nimish, 2026-11-03: "I want to understand what the final consistent structure will look like. Even though we build it
for K2, what are those key moving modules in the entire system? What are we building now? What remains to be built? …
each of these elements is being built with a lot of rigor and testing. Independently, it works, and then each of these
connects very well."

## 0. The two jobs

Nimish, 2026-11-03:

- "The core part of this system is how we are going to be mapping, tracking, and creating progress for every child."
- "Today, teachers spend a significant amount of time on building timetables manually, copy-pasting, preparing for
  the next day, and creating checklists … This is a system that works for the teachers in the school."

So every module serves one of two jobs, and is judged by it:

1. **Each child's progress.** The layers L5–L6 below: one evidence store, one derived picture per child, built only
   from confirmed evidence.
2. **The educator's offhand work, done by the system.** The layer L4 and its outputs: the week drafted, not built by
   hand; the checklist drawn from the plan, not copied; tomorrow's activities and materials already on the phone.
   The test is minutes taken away, not features added.

A module that serves neither is not built.

## 1. One structure, seven layers

Every module reads or writes one layer and hands over to the next through a table, never through another module's
code. The layers are listed from why to what reaches a parent.

| # | Layer | Answers | Rows (today's table, or the one proposed) | State |
|---|---|---|---|---|
| L1 | **Why** | What should a 16-year-old be? | `word` (the three words, rows: see below) → `capability` (the graduate profile's 8) → `capability_behaviour` per stage (192 drafted on 26 Sep, council-checked, **not yet accepted by the founders**) | drafts in `docs/school-os-level2-*`; no tables |
| L2 | **What, across ages** | What can a child do, at any age? | `domain` (14) → `skill` (244, the registry) → `milestone` per band; outside frameworks (NCF-SE, NCERT, Cambridge) as signed claims on skills and objectives (ADR 0041) | registry **live**; crosswalk as data files, tables **proposed** |
| L3 | **What, in this grade** | What is taught here? | Grade 1+: `subject` → `topic` → `learning_objective` (1,750, G1–G4) → skills. Pre-primary: pillar (`trait`) → room or strand → `activity` (2,216, PG–K2) with its own levels → skills | **live** as rows; authoring screens for maths and English only |
| L4 | **When** | What happens this fortnight, this week, this period? | `academic_year` → `fortnight` → `plan_entry` → `timetable_version`/`timetable_slot` → `week_plan` → `session` | **none** (ADR 0098, T1–T3) |
| L5 | **What happened** | What did the child do? | `evidence_event`, one store, every kind: written (papers), observed (taps), voice, project, performance; each names a registry skill, who saw it, where, its source | written **live** (maths); observed **schema only** (C2) |
| L6 | **What it means** | Where does each child stand? | derived, rebuilt nightly: `child_skill_state` (maths, live), `child_activity_state`, `child_pillar_state`, `class_coverage`, `unobserved_child` (proposed) | maths **live**; the rest **none** |
| L7 | **What we say** | What do the educator, coordinator and parent see? | `class_card`, `home_sheet`, `parent_note` (live for maths), `report_draft_line` (proposed), the Holistic Progress Card shape later | maths **live**; K2 **none** |

Around the layers sit five things every module shares:

- people and classes (`staff`, `school_class`, `enrolment`: proposed, ADR 0098 T0);
- one approval list (`approval`, live, C5);
- curriculum versions (`curriculum_version`, live, C3);
- consent and the data register (live, C6);
- prompts with their evals (`prompt`, live).

### The three words, and what each is measured by

The educator brochure says **capable, kind and confident** (Nimish, 2026-11-03). The words have changed several
times. The brain's `open-questions.md` holds:

- "Capable, Kind, Unafraid" (22 and 25 Sep, 9 Oct);
- "Kind, Curious, Unafraid" (the Brand Book);
- "five sacrosanct statements" (30 Sep).

None is marked final. That is why the words are rows (`word`): renaming one is an update of a row, never a code
change. Before a report card prints them to a parent, the founders sign one set.

Nimish's reading, 2026-11-03: "capability is going to be more around the mastery of skills". That gives each word a
different kind of evidence. The structure turns on this:

| Word | Measured by | Evidence | Layer |
|---|---|---|---|
| **Capable** | mastery of skills: the child's state on each registry skill, from papers (Grade 1+) and activity levels (pre-primary) | written and observed, counted by code | L2 skills → L6 `child_skill_state`, `child_activity_state` |
| **Kind** | behaviours an adult sees and records, never a score (council rule 7: nothing scores a child's emotions) | observed notes tagged to behaviours | L1 behaviours → L5 `educator_note`, `evidence_event` kind `observed` |
| **Confident** | the same, for trying, asking, speaking up, showing work | observed notes, performance, the child's own voice | as for Kind |

So "Capable" is the assessment engine and the activity levels, both already shaped as skills. "Kind" and "Confident"
are the observation module's notes, tagged to the 192 drafted behaviours once the founders accept them.

### The frames that already exist, placed on this structure

The school has five frames for "the kind of child". They are not yet reconciled. This map places each one; the
founders decide the joins.

| Frame | Where it came from | Its place |
|---|---|---|
| 3 words (now "capable, kind, confident" in the educator brochure), 8 capabilities | graduate profile, Sep 2026; brochure | L1, the top |
| 5 pillars (independence, moral compass, respect, empathy, questioning) | brain `outcomes/`, a spine v0, mostly stubs | L1. To be mapped onto the 8 capabilities or retired; two tops is one too many |
| 7 pillars (Expression, Critical Thinking, Curiosity, Empathy & Happiness, Creativity, Courage, Independence & Discipline) | pre-primary curriculum and the K2 planner | L3 for PG–K2: how the curriculum is grouped. Each pillar maps to one or more capabilities |
| 5 report traits (primary) | the primary report card | L7: how a report groups lines. Each maps to capabilities |
| "11 statements, 23 skills", "5–7 qualitative attributes" | named on 2026-11-02 [unclear source] | not placed until their source is found |

**One join table settles it:** `capability_link` (frame, code, capability). Any pillar, trait or attribute names the
capabilities it serves. A K2 observation then reaches L1 through its activity: activity → skill → pillar →
capability. No frame is rewritten.

### The rubric unit: a contradiction to settle

- **28 Sep (ADR 0041, decision 3, "Decided"):** rubrics per *step of a strand*, four levels (Beginning, Developing,
  Secure, Extending). A rubric per objective was rejected: 1,750 objectives × 4 levels is 7,000 descriptors, "too fine
  to observe and too many to sign".
- **2 Nov (neosapien:e387ff40):** rubrics at *learning-outcome* level, with the timetable unit Topic–LO.
- **K2 reality:** levels per *activity* (L0–L3), written by teachers, already in the database.

These can all hold at once if each does a different job:

- the **plan and the timetable** place learning outcomes, or activities in pre-primary (2 Nov);
- **evidence** is counted per learning outcome, or per activity (code does this);
- the **rubric a person judges with** is per step of a strand from Grade 1 (28 Sep);
- in pre-primary the activity's own levels are the rubric.

If 2 Nov meant "a person writes a four-level rubric for every LO", it reverses 28 Sep and costs about 7,000
descriptors. **Decision needed from Nimish and Akanksha.**

## 2. The modules

A module owns its tables, has one job and is proved by its own goal (`goals/*.yaml`, 100% of its scenarios). It
connects to another only through a hand-over declared in `workflows.json`. `test_layout.py` already fails if code
drifts from that map, so "each works alone, and they connect" is held by a command, not a promise.

| # | Module | Layer | Owns | Hands to | State | When |
|---|---|---|---|---|---|---|
| 1 | **People and classes** | shared | staff, roles, classes, enrolment, campus, room | every module | `config` JSON today | K2 pilot, T0 |
| 2 | **Calendar** | L4 | academic year, fortnights, school days, events (minimal) | Plan, Timetable | none | K2 pilot, T1 |
| 3 | **Spine** (why and what across ages) | L1–L2 | capabilities, behaviours, registry, crosswalk claims | Curriculum, every report | registry live; L1 drafts; crosswalk files | registry now; L1 and crosswalk tables after the founders' sitting |
| 4 | **Curriculum design** | L3 | topics, objectives, activities and levels, lesson plans, TLMs, skill sets (maths, English) | Plan, Assessment, Materials | maths and English authoring live; K2 activities loaded; no lesson-plan or TLM authoring | K2 lesson plans and TLMs in T2; full authoring module after the pilot |
| 5 | **Plan** (fortnight) | L4 | `plan_entry` | Timetable, Coverage | none | K2 pilot, T2 |
| 6 | **Timetable** | L4 | template, slots, weeks, sessions | Today, Coverage | none | K2 pilot, T3; solver later |
| 7 | **Assessment** (W1–W4) | L5 | bank, papers, reading, marking, written evidence | Graph, Reports | **live** for maths; English Grades 3–4 in progress; Hindi educator-marked | continues |
| 8 | **Observation capture** (Today) | L5 | attendance per session, `activity_observation`, `educator_note` | evidence_event | schema only | K2 pilot, T4 |
| 9 | **Child graph** | L6 | the derived states | Profile, Reports, Plan (next week) | maths live | observation states in T5 |
| 10 | **Coordinator view** | L6–L7 | nothing (reads) | — | Today and across-classes pages live for maths | K2 in T5 |
| 11 | **Materials** | L4 | monthly list | Radhika | none | T6; inventory later |
| 12 | **Reports** | L7 | class card, home sheet, parent note, report draft lines | parents, after two approvals | maths live | K2 report draft in T7; HPC shape later |
| 13 | **Events** | L4 | event, its steps, roles, parent messages | Calendar, Materials | none | dated entries in T1; full module later |
| 14 | **Parent channel** | L7 | what a parent sees, consent | — | none | after the pilot |
| 15 | **Tasks and messages** (@-tag) | shared | task | — | none | later |
| 16 | **School admin** (fees, admissions, attendance, payroll) | outside | — | exports | Kreeyo, sheets | buy or integrate, never build |

## 3. How the modules connect: the K2 week as one chain

The hand-over each arrow crosses is what a contract test checks. One end-to-end goal, `goals/k2-week.yaml`, runs the
whole chain on a fresh database. It checks each step's output independently of the code that made it.

```
Curriculum (activity + levels + TLM)        People (K2, Swarupa ma'am, 22 children)      Calendar (FN 10, school days)
            \                                          |                                       /
             └────────────────> Plan: plan_entry (FN 10: Brown Stairs, 3 periods) <──────────┘
                                         │  Friday: engine drafts the week; coordinator approves; educator confirms
                                         ▼
                              Timetable: week_plan → session (Tue 10:20, Block Room)
                                         │  Today on a phone: attendance, tap L0–L3 per child, optional note
                                         ▼
                      Capture: activity_observation ──confirm──> evidence_event (observed, per skill)
                                         │  nightly: engine graph
                                         ▼
                 Graph: child_activity_state · child_pillar_state · class_coverage (not done → next week's plan)
                                         │
                                         ▼
          Reports: report_draft_line (cites evidence) ──educator──> coordinator ──> parent (after the pilot)
```

Assessment joins at the same two points it already uses:

- its written evidence lands in the same `evidence_event`;
- the graph reads both kinds into one child.

A Grade 1 child's profile then shows both their papers and their observations on the same skills.

## 4. How each module is proved before it is connected

This repository's existing rules apply to the Teacher OS unchanged. They are named so nobody invents a looser
process for the new modules:

1. **A goal before code** (rule 12): a sentence of Nimish's, scenarios in the school's terms, 100% or not done.
2. **The module alone:** its own test file and its own goal. Fixtures are rows, never names (rule 6).
3. **The hand-over:** declared in `workflows.json`; a contract test feeds the upstream module's real output to the
   downstream one.
4. **The chain:** `goals/k2-week.yaml`, end to end on `bin/testdb fresh`, before any K2 slice is called done.
5. **On live:** each slice is rehearsed on a copy of live first (`rehearse update-live`). Past evidence is
   fingerprinted before and after (`engine past`), unchanged.
6. **With the educator:** Swarupa ma'am's week, measured: minutes per day on the system, taps per activity, her
   Friday rating. A slice that adds minutes is not done, whatever its tests say (the council's rule 10: measure
   teacher time before and after every assistant).

## 5. What is being built now, and what is not

**Now, for K2 (ADR 0098, T0–T7, by 2026-12-31):** modules 1, 2, 5, 6, 8, 9 (observation states), 10 (K2),
11 (list only), 12 (K2 draft), and module 4's lesson plans and TLMs for K2.

**Continues beside it:** module 7, Assessment: English Grades 3–4, the remaining S slices. Their order against T0–T7
is Nimish's decision, which BUILD-ORDER records.

**Not now, and why:**

| Not now | Why | Comes when |
|---|---|---|
| Curriculum authoring for every grade, drag-and-drop | K2's curriculum exists; a canvas for one class re-plans nothing | a second class joins |
| Timetable solver | one class, one template | shared subject educators (Grades 2–5, campus two) |
| L1 tables and the crosswalk tables | wait for the founders' sitting on the 192 behaviours and on `capability_link` | after that sitting |
| Voice split across many children | taps first; teachers say audio goes unused | the educator asks for it |
| Parent channel | needs two-person release and the consent register in use | after the K2 report draft works |
| Full events, inventory, tasks | do not block the K2 loop | after the pilot |

## 6. What is adopted, not built

To be completed from two surveys running on 2026-11-03: the educator-app UX study (Kreeyo, Toddle, Tapestry, Famly,
Transparent Classroom and others) and the open-source survey (Gibbon, OpenEduCat, FET, Timefold, OneRoster, CASE,
drag-and-drop and offline libraries). Each module will name what it adopts, what it borrows, and what it builds.
