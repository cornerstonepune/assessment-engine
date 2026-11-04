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

## Found in the school's sheet (for the coordinator to settle)
- **Number names 11-20 gives its objective as "numbers from 6-10"**: a copy slip. Shown as written, with Correct.
- **Two plan items have no activity row:** Clay "carrot, chillies, apple" (clay rows read: about 20 of 21) and Block Room "Smelling Bottles" (not among its 35 names). Chip "Plan"; M1-11 drafts the row.
- **Reminder dates fall in the vacation:** 9 and 16 Nov for FN10 (vacation 4-17 Nov). Rule from the orchestrator: send on the last working day before; if past, send at once. FN10's list is asked for now. Shown on screen 5.
- Four rows read in full (Insects, Butterfly, Number names 11-20, Addition orally P1): all have steps, rubric and materials, none has "how to think". One level reads "ableto"; shown verbatim.

## What is missing, and how a screen shows it
1. "How to think about it": no field. "Not written yet" only until the M1-11 agent drafts it; then the text shows tagged Drafted with Keep, Change, Reject (screen 3b; the school's words keep the School tag, a person's change shows Edited). She can write it herself now.
2. Quantity and unit: the sheet has none. Blank until the agent drafts them as catalogue items (D-071). New items go to review.
3. Level 0-3: numbers only, no Easy/Medium/Hard/Advance on K2. D-051 and the sheet give no words for the numbers; none is shown.
4. Stock versus request (chalk, black board): she ticks what she has; the rest is sent.
5. Send is WhatsApp first (one tap opens it with the list written out), email second. It records what was sent, not that it was read.

## Decisions recorded (orchestrator, 4 Nov)
- Both FN10 reminders due now: one message, not two.
- "Team has it", ticked by her, is enough team confirmation for v1.
- Her reminder channel: in the app plus email to her school address.
- Still a placeholder: the team's WhatsApp number or group, until Nimish names the person.

## Questions for a person
- The materials team's WhatsApp number or group (placeholder on screens 4-5); is email to the team also wanted?
- Words for Level 0-3 on K2 (a legend such as 0 not yet, 1 beginning, 2 expected, 3 stretch exists nowhere I could find). The M1-11 card still says "Easy/Medium/Hard/Advance rubric": to reword.
- Anchor for reminders: first day a material is needed (M1-10) or the fortnight start? Screens use the first day needed.
- Who may revert a correction: the coordinator (orchestrator, 4 Nov). FN10 end date: roadmap 4 Dec, Graph 7 Dec (M1-06 holds this).

## Tables and engine calls (proposed; reuse M1-06's `fortnight`, `school_day`, `period`, `timetable_slot`, `plan_entry`, `session`)
- New: `activity_thinking(activity_id, text, state proposed|approved, author, approver, at)`; `materials_list(class, fortnight, state draft|sent, route whatsapp|email, sent_by, sent_at, sent_body)`;
  `materials_line(list, catalogue_item, activity_id, first_needed, qty, unit, have, added_by)`; append-only `materials_line_edit(line, who, at, before, after)`; `reminder(list, kind 2w|1w, due, to, channel, sent_at)`. 
- Also: `activity_edit(activity, part, who, at, before, after, reverted_by)` for corrections (revertable by the coordinator); parts carry a source tag school|drafted|edited from M1-11's ledger.
- Engine endpoints (thin, one per screen): day, week, `period/{slot}` (fields plus where each came from), `materials/collate`, line add/change/remove, `materials/send`, `engine reminders --due`.
- n8n only triggers and delivers (rule 3): a daily run calls `reminders --due` and sends what it returns; a sent list cancels later reminders.
- Goals to write first: `goals/m1-09-educator-timetable.yaml`, `goals/m1-10-materials-list.yaml` (scenarios S-M1-09-click, S-M1-10-materials in teacher-os).

## Verified
- `python3 build.py` (kept off git) wrote `index.html`; Playwright screenshots at 1360 px show desktop and phone folding to one column on all five screens. Not run: `bin/check`, `pytest` (no code changed).
- Not verified: the activity matching (plan line to row) beyond the four rows above; the generator's placement of topics (illustration, labelled so).
