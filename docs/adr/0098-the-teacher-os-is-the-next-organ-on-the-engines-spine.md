# 0098 — The Teacher OS is the next organ on the engine's spine: one database, K2 first, tables ready for every grade

Date: 2026-11-03
Goal: none — a design proposal that builds nothing. Each slice below starts with its own goal file (rule 12) once
`BUILD-ORDER.md` names it.
Status: **proposed** — needs Nimish's ratification, and a line in `BUILD-ORDER.md`. Until then BUILD-ORDER binds as
before.
Product scope: `cornerstonepune/cornerstone-brain` → `domains/tech-product/teacher-os.md` (what, for whom, by when, open
questions). This file is how it is built.

## Context

Nimish and Akanksha, 2026-11-02 (NeoSapien, 13:58–17:06), decided on a Teacher OS pilot:

- one class, **K2**, with Swarupa ma'am and a second educator not yet named;
- a base version in about two weeks;
- by **2026-12-31**, the whole K2 loop on the system: timetable → curriculum → observation and feedback → evaluation.

Three outcomes for March 2027:

- no spreadsheets;
- report cards made of accumulated observations;
- no more than 20–25% of an educator's time on admin.

Nimish's words: "right from the timetable to the curriculum to measurement that feedback loop along with assessment ...
this is being done through a system." He asked that it be "completely scalable": the data, the tables and how the
parts interact, thought through now for one class.

What the database already holds for K2, read on 2026-11-03:

| Already here | What it gives the Teacher OS |
|---|---|
| `activity` (590 K2 rows), `activity_skill` | K2's whole activity list from "(K2) Sr kg Planning Sheet_26-27", with the teachers' level words (`level_1`..`level_3`) and registry skills |
| `report_item` (126 K2 rows) | every line of the K2 report card, keyed to a skill |
| `trait` | the seven pillars per band (IND, EXP, CRT, …) |
| `grade`, `subject`, `topic`, `skill`, `learning_objective` | the curriculum spine; LOs exist for G1–G4 |
| `evidence_event` with `kind`, `mark`, `seen_by`, `place`, `source` (C2) | an observed record is already allowed; nothing writes one yet |
| `evidence_scale`, `evidence_mark`, `evidence_kind` | scales are rows; a new scale is an insert |
| `approval`, `approval_kind` (C5) | one approval list; a new thing to approve is a new kind |
| `curriculum_version` (C3) | edits take effect from the next week |
| `consent`, `data_register` (C6) | what is kept about a child, and why |
| `child`, `pii.child`, `child_move` | children, names apart |

What is missing:

- staff live in one settings row, `config` `app.staff`, as JSON;
- a class is two text fields on `child` (`band`, `section`);
- there is no campus, room, calendar, fortnight, timetable, lesson plan, TLM, delivered session, attendance or observation capture.

## Decision

### 1. One database, one site

The Teacher OS adds tables to this Postgres and pages to `apps/web`. It is not a second app.

- **Blueprint v2, rule D1:** "how is this child doing?" is a join, and joins do not cross databases.
- **ADR 0036:** the school OS grows from this spine.
- **The 22 Oct locked scope:** a phone dashboard for educators, no WhatsApp; KG assessed by observation on a phone (S9).

The K2 pilot *is* S9, widened to the educator's whole day.

### 2. The rubric sits on the observable unit

In K2 the observable unit is the activity; from Grade 1 it is the learning objective. Both name registry skills, which
is where profiles and reports join.

On 2026-11-02 the hierarchy Subject → Topic → Learning Outcome was agreed, with rubrics at LO level. K2's curriculum
is not shaped that way. It is about 590 activities under a pillar and a room. Each has level words its teachers wrote,
from L0 "doesn't sit for the class" to L3. Rewriting them as LO rubrics would take the pilot.

So a plan entry, a delivered session and an observation each point at **either** an activity **or** a learning
objective (exactly one, by a check). Both lead to skills through `activity_skill` or `learning_objective_skill`.

### 3. The pilot's loop needs no model

The loop is plan → week → session → tap per child → evidence → profile → report. Each step is code and a person.

A model is used in three places only. Each has a prompt row and an eval (rules 2 and 7), and none blocks the loop:

- writing the educator's optional voice note as text (an adapter);
- matching the Monthly Planner's free text to activity codes, once, at load (proposed, a person confirms);
- drafting report sentences from cited evidence (every citation checked by code).

### 4. Tables now for what screens come later

The tables carry what drag-and-drop editors and a timetable solver need from day one:

- an `ord`;
- a `fortnight` on every plan entry;
- staff and rooms on every slot;
- a campus on every class and room.

The screens wait until more than one class uses them. A drag is then an update of `ord` or `fortnight_id`, through an
approval when the week is already approved. A solver (FET, as the council named, or OR-Tools CP-SAT; to choose when
needed) reads the same rows and proposes a template version. A coordinator approves it.

### 5. Every new table follows this repository's rules

- `tenant_id` and RLS on every table.
- Names in `pii` only.
- Structure as rows (rule 1).
- The truth tables append or approve, never edit (ring A).
- The derived tables can be truncated at any time (ring B).
- n8n fires triggers and sends notices; it decides nothing (rule 3).

## The tables

Names singular, as the repository does. "New" means a numbered migration in its slice.

### People and places (slice T0)

| Table | Ring | Holds |
|---|---|---|
| `campus` | A | id, name. One row today; campus two is an insert |
| `room` | A | campus, name, kind (classroom, block room, outdoor…), capacity |
| `staff` | A | id, active, the classes and roles below; **no name** |
| `pii.staff` | A | staff_id, name, email, phone; read only through the logged accessors, as `pii.child` is |
| `staff_role` | A | rows: educator, coordinator, head, specialist, support |
| `staff_role_grant` | A | staff, role, from, to |
| `academic_year` | A | code (2026-27), start, end |
| `school_class` | A | campus, academic_year, grade (key to `grade`), section, room |
| `enrolment` | A | child, school_class, from, to. Replaces `child.band` and `child.section` as the truth; those stay readable one deploy, then go |
| `class_staff` | A | school_class, staff, role in the class (class educator, assistant, specialist), subject or strand if any, from, to |

`app.staff` is copied into these, every reader is moved, and the config row goes. Sign-in is unchanged: same email,
same password hash. ADR 0073's role checks read `staff_role_grant`. ux9c's "every feature is every member of staff's"
still holds.

### Calendar (slice T1)

| Table | Ring | Holds |
|---|---|---|
| `fortnight` | A | academic_year, ord, start, end, theme ("The five senses and my school") |
| `school_day` | A | date, kind (teaching, holiday, settling, event-only), note; a day override is a row |
| `event_type` | A | rows: daily activity, classroom event, school-wide, field visit |
| `event` | A | type, date or range, school_class or none (school-wide), owner role, title, purpose |

### Curriculum plan (slice T2)

| Table | Ring | Holds |
|---|---|---|
| `activity_level` | A | activity, ord (0–3), words. Replaces `level_1`..`level_3` and adds L0, which the sheet has and the table lost |
| `lesson_plan_version` | A | activity or LO, version, steps, periods, written by, approved by and when; the newest approved is current |
| `tlm` | A | code, name, unit (the sheet's TLM No. kept as a code) |
| `activity_tlm` | A | activity, tlm, quantity |
| `plan_entry` | A | curriculum_version, school_class (or grade), fortnight, activity **or** LO, periods planned, ord. The Monthly Planner as rows |

Two approval kinds are added to `approval_kind`: `activity_change` and `week_timetable`. They use the agreed path:
the educator suggests, the coordinator checks, and the head decides on philosophy. Rows, not code.

### Timetable (slice T3)

| Table | Ring | Holds |
|---|---|---|
| `period` | A | grade or school_class, ord, start, end, kind (routine, teaching, break). K2 has about 15 bands, 08:30–13:25 |
| `timetable_version` | A | school_class, from date, approved by |
| `timetable_slot` | A | version, week of fortnight (1 or 2), weekday, period, strand or subject, staff, room |
| `week_plan` | A | school_class, week start, state (draft, approved, confirmed), approved by, confirmed by |
| `session` | A | week_plan, date, period, plan_entry, staff, state (planned, done, not done, moved), moved to |

Friday, n8n calls the engine. The engine drafts next week from the template, the fortnight's plan entries and last
week's not-done sessions. The coordinator approves; the educator confirms or edits. Once a week is approved, a
change is a new row, never an edit.

### Capture (slice T4)

| Table | Ring | Holds |
|---|---|---|
| `session_attendance` | A | session, child, present. An absent child cannot be given a mark (Blueprint v2's voice-flow rule) |
| `activity_observation` | A | session, child, mark, observed by, observed at. Append-only; a correction supersedes |
| `educator_note` | A | school_class, date, child or none, pillar codes, text, audio key (storage, never git or a log), observed by |
| `evidence_scale` row `activity_level`, `evidence_mark` rows `l0`…`l3`, `not_willing` | A | an insert, as C2 made scales rows |

When an educator confirms a session, code writes one `evidence_event` per skill the activity names. Each has
kind `observed`, mark on `activity_level`, `seen_by` the educator, `place` the session and `source` the
`activity_observation` id. `evidence_event` stays the one store and stays append-only (rule 4). The maths graph still
reads written answers alone (`evidence_placed`).

### Derived (slice T5, ring B, rebuilt by `engine graph`)

| Table | Holds |
|---|---|
| `child_activity_state` | each child × activity: latest mark, count, first and last seen, a dip (a lower mark after a higher one) |
| `child_pillar_state` | each child × pillar: observations this fortnight, last seen |
| `class_coverage` | school_class × fortnight: planned, done, not done, carried |
| `unobserved_child` | children with no observation in N days (N a `threshold` row) |

### Materials and report (slices T6, T7)

| Table | Ring | Holds |
|---|---|---|
| `materials_list` | A | school_class, month, state, confirmed by; lines are computed from `plan_entry` × `activity_tlm` and kept as they were confirmed |
| `report_draft_line` | A | child, report_item, words, evidence ids cited, prompt version, validated by, released by. Every citation is checked by code; the educator validates each line; the coordinator releases (decision class: anything a parent sees, two people) |

## How the parts talk

```
plan_entry ──(Fri, n8n → engine)──> week_plan ──coordinator approves──> educator confirms
     │                                   │
     │                               session ──(Today, phone)──> attendance + activity_observation
     │                                   │                               │
     │                           not done → next week          confirm → evidence_event (observed)
     │                                                                   │
activity_tlm ──(23rd, n8n → engine)──> materials_list            engine graph (nightly)
                                                                         │
                                       child_activity_state · child_pillar_state · class_coverage
                                                                         │
                                       report_draft_line ──educator──> coordinator ──> parent (later)
```

n8n's whole part is three schedules and two notices:

- the Friday week draft;
- the 23rd materials list;
- the nightly rebuild;
- "your week is ready to confirm";
- "no observations from this class in 7 days".

## Slices, in order

Each slice needs a goal file before code, and C slices' rule holds: one schema change at a time. The dates are
estimates, not a measured velocity.

| Slice | Green means | By (estimate) |
|---|---|---|
| T0 | every person in `app.staff` and every child appears exactly once in `staff`/`pii.staff`/`enrolment`; sign-in and every page unchanged; `app.staff` read by nothing | 2026-11-09 |
| T1 | K2's fortnights, school days and the 2026-27 holidays are rows, loaded from the planning sheet's Graph tab and the Event + Holidays calendar; a count matches the sheet | 2026-11-11 |
| T2 | K2's activities carry L0–L3 as rows, lesson plans and TLMs as rows, and every fortnight of the Monthly Planner is `plan_entry` rows that a person has confirmed against the free text | 2026-11-16 |
| T3 | a K2 week is drafted from rows, approved and confirmed on the site; a not-done session reappears next week | 2026-11-18 |
| T4 | on a phone, Swarupa ma'am marks a real activity for the real class in under a minute, and the evidence rows appear with her name, the session and the skills | 2026-11-23 |
| T5 | a child's profile and the coordinator's class view show what T4 wrote, rebuilt from nothing byte-identical | 2026-12-04 |
| T6 | December's materials list drafted from the plan, confirmed, and sent | 2026-11-24 for December |
| T7 | one K2 child's report draft, every line citing evidence, validated and released by two people | 2026-12-23 |

## Rejected

| Alternative | Why |
|---|---|
| A separate Teacher OS app and database | Splits the child across two stores; Blueprint D1 and ADR 0036 already chose one |
| WhatsApp bot as the educator's channel | Decided against on 2026-10-22 ("a full dashboard for educators, on a phone too, no WhatsApp") |
| Rubrics on learning outcomes for K2 too | K2's curriculum is activity-shaped and its level words are teacher-written; the shared join is the skill |
| Drag-and-drop editors and a timetable solver in the pilot | One class has one template entered once; the tables carry ord, fortnight, staff and room so both come later without a migration |
| Voice-first capture (one note split across many children) | Today's K2 form is a tap grid; teachers told Nimish typing is easier and audio is not used (neosapien:c73174ce); name-matching risk on a small class buys nothing yet |
| A `teacher` table | The school's word is educator, and support staff, coordinators and specialists hold the same record; `staff` plus roles |
| Keeping staff as `config` JSON | No keys, no history, no per-class link; a timetable cannot reference it |

## Revisit when

- a second class joins: the drag-and-drop plan editor becomes worth building;
- two classes share a subject educator: the solver becomes worth choosing;
- an educator asks for voice over taps in the pilot, or taps are measured slower than notes;
- campus two opens: `campus` gets its second row and every view gains a campus filter.
