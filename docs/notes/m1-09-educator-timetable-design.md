# M1-09 / M1-10 — the K2 educator's timetable: design note (wireframes only; no code, no migration)

**Gate:** none fits, as for M1-06: `workflows.json` has no step for this, so step 1 of any build adds it. Pictures: `docs/screens/m1-09/index.html`
(desktop and phone of every screen; no PNG previews: the pictures are the HTML). Real lines from the K2 Planning Sheet 26-27 for FN10; no child names.

## Screens, what each shows, where it comes from today
| Screen | Shows | Source today |
|---|---|---|
| 1 Today | the day's periods in time order, one status chip each, "materials: not sent" link | M1-06 `timetable_slot`; chip from the activity row |
| 2 This week | Mon–Fri grid, toggle to next week; every box opens | M1-06 slots; topics are Monthly Planner lines |
| 3 One period | objective · what to do · how to think about it · rubric · materials, each with Correct | Activity list: Learning outcomes, Lesson plan, Level 0–3, TLMs |
| 4 Materials | one list by day / week / fortnight; tick "I have it"; add, change, remove; Send | TLMs of the planned activities |
| 5 Reminders | what she gets at 2 weeks and 1 week, what the team gets, what the team receives | new; nothing exists |
Two taps: Today → period (1); the rubric is on that page (phone: the Rubric jump, 2). Status chips: Ready, Part, Plan, Specialist, Free (colour + icon + one word; no red anywhere).

## What the real FN10 rows showed (read 4 Nov)
- Four rows read in full (Insects, Lifecycle of Butterfly, Number names 11-20, Addition orally P1). All have steps, rubric and materials; none has "how to think about it".
- **Number names 11-20 says its objective is "numbers from 6-10"**: a copy slip. Shown as written, with a Correct button.
- **Planner lines with no activity row:** Clay "carrot, chillies, apple"; Block Room "Smelling Bottles" (not among the 35 Block Room names). Chip "Plan"; the screen says so.
- Addition orally P2 has no period count; none of the four gives a quantity. Rubric text is shown verbatim (one level reads "ableto").
- Level 0 reads "does not concentrate in the class": it is shown neutral grey, never red.

## What is missing (not invented on any screen)
1. "How to think about it": no field. Proposal: a person writes it; mapping agents may propose, a person approves (one row per version, never overwritten).
2. Quantities: the sheet has none. Column says "not in sheet"; she may type one.
3. Level 0–3 against Easy/Medium/Hard/Advance: the sheet headers say only "Activity Level 0..3". Screen shows numbers until a person confirms.
4. Stock versus request (chalk, black board): she ticks what she has; the rest is sent. Alternative: the team marks stock items once.

## Questions for a person
- **O-39** how the materials team receives a request (address, sheet, WhatsApp). Placeholder `[team address]` on screen 5.
- Channel for her reminders: in the app on Today plus email? (No WhatsApp, 22 Oct.)
- **Vacation:** FN10 starts 23 Nov, so 2 weeks before is 9 Nov and 1 week before is 16 Nov; both are vacation (4–17 Nov). Send anyway, or on the first working day? For FN10 itself: send the list now?
- Is "first day a material is needed" the anchor (as M1-10 says) or the fortnight start? Screens use the first day needed.
- Confirm Level 0–3 = Easy/Medium/Hard/Advance. Does she correct activity text herself (22 Oct: every educator edits, effective next week) or only propose?
- FN10 end date: roadmap says 4 Dec, Graph says 7 Dec (M1-06 holds this).

## Tables and engine calls (proposed; reuse M1-06's `fortnight`, `school_day`, `period`, `timetable_slot`, `plan_entry`, `session`)
- New: `activity_thinking(activity_id, text, state proposed|approved, author, approver, at)`; `materials_list(class, fortnight, state draft|sent, sent_by, sent_at, sent_body)`;
  `materials_line(list, text, activity_id, first_needed, qty, have, added_by)`; append-only `materials_line_edit(line, who, at, before, after)`; `reminder(list, kind 2w|1w, due, to, channel, sent_at)`. Activity corrections go through the existing `approval`.
- Engine endpoints (thin, one per screen): day, week, `period/{slot}` (fields plus where each came from), `materials/collate`, line add/change/remove, `materials/send`, `engine reminders --due`.
- n8n only triggers and delivers (rule 3): a daily run calls `reminders --due` and sends what it returns; a sent list cancels later reminders.
- Goals to write first: `goals/m1-09-educator-timetable.yaml`, `goals/m1-10-materials-list.yaml` (scenarios S-M1-09-click, S-M1-10-materials in teacher-os).

## Verified
- `python3 build.py` (kept off git) wrote `index.html`; Playwright screenshots at 1360 px show desktop and phone folding to one column on all five screens. Not run: `bin/check`, `pytest` (no code changed).
- Not verified: the activity matching (plan line to row) beyond the four rows above; the generator's placement of topics (illustration, labelled so).
