# M1-06 — K2 timetable generated from the plans (design note, step 1; no code, no migration)

**Gate:** none fits. `workflows.json` has no step for plan or timetable (nearest: W2 N4 "the week's declaration"; N12 is
reports). CLAUDE.md says change the map first, so the first commit of step 2 adds the step to `workflows.json`. Needs a yes.

## Surprises (plainly)
- No tab is called "Time table 26-27". Three exist: `F.N - Time table 26-27` (two weeks), `Sample_Time table 26-27` (one week),
  `Time table 25-26`. They disagree. The census says "mostly blank": wrong. Every slot names its subject; only the topics are blank.
- The `Fortnights` folder holds no plans: about 50 pictures of rhyme and story props, flashcards and sheets, dated April 2025.
- The Monthly Planner's headings for Nov onward still say "2025" and "January 2026"; Fortnight 9 appears twice with different
  text; Fortnight 1 text matches last year's hand-filled sheet. It looks copied forward. Worth the coordinator confirming it is current.

## (a) What the plans give for Nov to Mar
- Monthly Planner: one row per fortnight, 8 columns: English+Hindi+stories+rhymes; Math+Block room; Brave Day task; General
  Awareness; Art, Clay, Music; Circle time, Good deed, Word of the week, Prayer; motor skills, routines, PE; events.
- Dates are on `Graph_2026-27`: FN10 23 Nov–7 Dec, FN11 8–20 Dec, FN12 4–17 Jan, FN13 18–31 Jan, FN14 1–14 Feb, FN15 15–28 Feb,
  FN16 1–14 Mar, FN17 15–28 Mar. Vacation 4–17 Nov and 25 Dec–3 Jan; buffer weeks 18–22 Nov and 21–24 Dec. Today (4 Nov) is
  vacation, so **FN10 is the first fortnight to generate**. That is 8 fortnights, 16 weeks.
- Gaps: topics are per fortnight, never per day or period, and are free text, not activity ids. Block Room, Gross Motor and
  Writing have planner lines but no slot in the F.N timetable (Block Room is only in the Sample tab). Not verified: how many of
  the 871 loaded activities carry a fortnight and a period count (the sheet has both columns, the sample rows are blank).

## (b) The period frame (`F.N - Time table 26-27`)
Mon–Fri, two weeks (A, B), 15 rows: 08:30 settling; 08:50 circle; 09:10 fruit; 11:45 lunch; 1:15 reflection; 1:20 dispersal;
1:25 bus. These 7 are fixed daily. The other 8 (09:40 10:00 10:20 10:40 11:00 11:20 12:15 12:40) are subject slots: 40 a week.
Weekly fixed: Monday memory drawing, Thursday no-screen day, Friday brave-day task. Unlabelled gaps 08:45–08:50, 1:05–1:15.
Empty cells: about 8 in week A, 3 in week B (my count; verify). PE and guest music are led by specialists, not the K2 educator.
Holidays: `Graph` holiday row looks stale (Holi 25 Mar, Good Friday 29 Mar, Women's Day "6 Mar Monday" fit 2024 and 2023; I am not
certain). The dated source is `Pre-Primary Calendar 26-27` (has a SCHOOL HOLIDAYS column; I read to 30 Jun only; Nov–Mar next).
Unknown: do K2 children attend the "Working Saturdays" (they look like educator days)?

## (c) Missing rule data, smallest way to get it
Do not derive it from the planner. Count it from the timetable itself. Week B per week: Math 5, English 4, Reading 4, Story 3,
Phonics 2, Hindi 2, General Awareness 2, Me time 2, Rhymes 2, Music 2, one each of Art, Clay, PE, play projects, routine of month,
fine motor, memory drawing, life skills, clean-up (3 empty). The code reads the sheet into `timetable_slot` rows; a person
corrects a draft (the empty cells, A versus B, where Block Room goes) rather than typing a frame. The planner supplies content only.

## (d) The generator (rule-based, one class, one educator; CP-SAT stays for Grades 3–4, D-024)
For each fortnight and subject: take that subject's planner lines in order and fill the subject's slots, week A the first half,
week B the second. Stories and rhymes: item 1 in week A, item 2 in week B (last year's hand-filled FN1–FN2 does exactly this:
verified in `Fortnight time table 2025-26`). Header rows from the planner. A line is only ever copied, never written by a model.
Slots led by specialists stay marked. Re-running an unchanged week gives identical rows (D-018: rolls forward, no approval).

## (e) Tables
Exist: `academic_year`, `school_class`, `enrolment`, `staff`, `staff_role_grant`, `subject`, `activity`, `approval`,
`activity_observation` (its `session_id` points at nothing yet). Missing, all eight named in modules.md: `fortnight`,
`school_day`, `period`, `timetable_slot`, `plan_entry`, `session`, `week_plan`, `timetable_version`. Proposal: first migration
the first six; `week_plan` and `timetable_version` with the approval step. `plan_entry` carries an optional activity id: planner text is never presented as an outcome; mapping lines to activities is a later step (M1-05). Rehearse on a copy of live first.

## (f) Goal and checks
**Goal:** the K2 coordinator opens the generated 23 Nov–7 Dec timetable, every period carries what the plan says for that
subject, and she changes only what is wrong. Machine checks, expected output fixed by a person (D-028):
1. Frame: 10 school days × 15 rows, correct dates, no teaching day on a school holiday; equals the frame the coordinator corrects.
2. Provenance: every slot text is a planner line of its own subject and fortnight; every planner line is placed or listed "no slot".
3. FN10 equals the coordinator's line-by-line marks (frozen by checksum, not in git). 100%: the rules change until nothing is
   changed. FN11 is then generated unseen and her edits are counted and reported, not a pass bar.
4. Roll-forward: unchanged week gives identical rows and no approval; one changed line flags exactly one.
5. No child name appears in any file, log or fixture (D-021).
**Open for a person (defaults in use):** current tab = `F.N` (A/B); Block Room, Gross Motor, Writing lines stay "no slot"; planner FN10–17 treated as current but the coordinator confirms; the K2 educator marks FN10; Working Saturdays left out. **Date conflict:** Graph says FN10 ends 7 Dec and FN11 starts 8 Dec (a Tuesday): not both right. The generator holds such a day back and lists it, never chooses. Week-A frame leftovers ("Rani's story", "Self - Introduction") need clearing.
