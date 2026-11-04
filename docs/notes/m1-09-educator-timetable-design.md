# M1-09 / M1-10 — the K2 educator's timetable: design note (rev 4; wireframes only, no code, no migration)

**Gate:** none fits (as for M1-06): `workflows.json` has no step for this, so step 1 of any build adds it. Pictures: `docs/screens/m1-09/index.html`
(7 screens, desktop and phone). Every element stays visible; long text sits behind a "Full text" or "Details" tap. Real FN10 lines from the school's sheet; no child names.

## The screens (every part visible; few words in each: label, chip, number, icon)
1 Today · 2 This week · 3 One period (Objective, What to do, How to think, Rubric, Materials, all on the page; long steps and objective clamp to one line with "Full text") ·
4 A drafted part (Keep / Change / Reject) · 5 Materials (day / week / fortnight, each line linked to its activity) · 6 Reminders · 7 The month (coordinator).
Two taps: Today → period (1) → Rubric is already on the page (2 = scroll or none).

## One vocabulary, every screen: round chip = icon + colour + one word
Do now (dark) · To confirm (amber) · Coming up (grey ring) · Done (green) · Late (terracotta hourglass: work only, never a child; the design language's red token).
Do now is the period in progress; To confirm is a part waiting for her (objective to check, draft to keep); Done and Late need a recorded note
(M1-04), so until recording runs only Do now, To confirm and Coming up can show. Statuses on the wireframes are an example moment (Mon 23 Nov, 11:35).
Small round icons say where text came from: book = School's own words, sparkle = Drafted by the agent, pencil = Edited (who and when kept; the coordinator can revert).
Materials lines carry Class / School / Not tracked tags (M1-13); the tags are placeholders, no homes or rupee values exist yet.

## Found in the school's sheet (for the coordinator)
- Number names 11-20 gives its objective as "numbers from 6-10": a copy slip. Shown as written, with Correct.
- Two plan items have no activity row: Clay "carrot, chillies, apple" (about 20 of 21 clay rows read) and Block Room "Smelling Bottles" (not among its 35 names).
- Reminder dates for FN10 (9 and 16 Nov) fall in the vacation. Rule (orchestrator): last working day before; if past, at once. FN10's list goes now, as one message.
- "How to think about it" has no field: "Not written yet" until the M1-11 agent drafts it, then it shows a sparkle and Keep / Change / Reject. She can write it now.
- Quantity and unit: none in the sheet; drafted later. Level 0-3 shown as numbers only; no words for them exist in D-051 or the sheet.

## The month (screen 7, D-072, M1-12)
Stepper with editable per-school dates (orchestrator, 4 Nov), for month M: draft ready by the 10th of M-1, frozen by the 12th, aligned by the 15th, approved by the 18th,
educators sign off the list by the 20th, list out by the 21st (10 days before M). December: Tue 10, Thu 12, Sun 15, Wed 18, Fri 20, Sat 21 Nov. Reminders 2 and 1 weeks. FN10 is the named exception.
She sees only a small lock marked Frozen on her week. After the freeze a change needs a reason, recorded with who and when.
**Finding:** for December the draft, freeze and alignment dates fall in the vacation (4-17 Nov per M1-06); the 15th is a Sunday and the 21st a Saturday.

## Other apps (searched and fetched 4 Nov; vendor claims, not tested by anyone here)
- **Kriyo** (confirmed as the app), staff-side iOS listing: QR and geo-QR attendance, teacher self check-in, daily records (meals, sleep, health), observations, assessments, learning outcomes, milestones, "activity planning", learning journals, daily reports, photos, parent notes, announcements, event reminders; "easy-to-use"; English only; 4.7 stars from 28 ratings. No lesson plans or timetable named. https://apps.apple.com/us/app/-/id1384125107
- Kriyo Parent listing: parents see attendance, daily diary, lesson plans, assessments, progress reports; pitched against "juggling WhatsApp groups, emails and paper notices". https://apps.apple.com/us/app/id1347533660 . Kriyo's own site returned 503 (https://www.kriyo.in); no teacher-app listing found on Google Play. Teacher screens never seen: unverified.
- Brightwheel: standards preloaded and editable; "easy and quick to make edits" to lessons; assessments "based on milestone or lesson progress". No activity library or phone editing on the page (a search summary said so; unconfirmed). https://mybrightwheel.com/features/learning/
- HiMama (search says now Lillio: unverified): "add or edit activities in your calendar"; "state standards listed on every activity"; "any device". https://wow.himama.com/sg_digital_curriculum/
- Toddle: a task links to its rubric, gradebook and portfolio; onboarding by a 1:1 walkthrough and an educator "Toddle Buddy"; K-12, early years only in passing. https://www.toddleapp.com/faqs/
- ClassDojo: free for teachers; Events with automatic reminders; messages translated into 190+ languages; nothing for preschool on the page. https://www.classdojo.com
- Seesaw: through search results only, not fetched: unverified. Not found anywhere: what India's pre-primary educators new to software struggle with.
**Changed because of them:** edit in place, no edit screen; the objective and rubric on the period page, as Kriyo and HiMama show outcomes with each activity; reminders automatic; WhatsApp stays the send route (Kriyo names it as the rival);
proposed: a short guided first session with Swarupa, not a manual. Not taken: points, portfolios, a parent feed (out of scope, and no red on a child).

## Decisions recorded (orchestrator, 4 Nov)
One message when both FN10 reminders are due now · "Team has it", ticked by her, is enough for v1 · her reminders: in the app plus email to her school address ·
send is WhatsApp first, email second (D-071) · she corrects activity text herself, the coordinator can revert · Late is terracotta (work only) · the month dates above are the defaults.

## Questions for a person
- New icons (Lucide, ISC, lucide-static 1.67.0): sparkles, book-open, lock, school, package, circle-minus, chevron-down, play. The orchestrator adds them to the gallery; design/README wants a yes.
- Do the month dates really run in the vacation, on a Sunday and a Saturday? Does "approved teacher-to-teacher" mean the educators of the month's activities (unverified)?
- Team WhatsApp number or group (placeholder). Words for Level 0-3. Anchor for reminders: first day a material is needed or fortnight start?

## Tables and engine calls (proposed; reuse M1-06's `fortnight`, `school_day`, `period`, `timetable_slot`, `plan_entry`, `session`)
- New: `activity_thinking`, `activity_edit(…who, at, before, after, reverted_by)`, `materials_list`, `materials_line(catalogue_item, activity_id, first_needed, qty, unit, have)`, append-only `materials_line_edit`, `reminder`.
  M1-12 and M1-13 own `month_cycle(state, who, at)`, the per-school setting rows, and item home and rupee value. Engine: one endpoint per screen; `engine reminders --due`; n8n only triggers and delivers (rule 3).

## Design tokens and audit (D-073)
`docs/design-tokens.md`, `apps/web/design-system/tokens.css`, `docs/design-audit-k2.md`: school palette, five chips, nine rules with checks, breaches by screen. The wireframes are not yet re-coloured (needs a go).

## Verified
- `build4.py` (kept off git) wrote `index.html`; Playwright at 1360 px shows all 7 screens, phone folding to one column; no Easy/Medium/Hard/Advance on any screen. Not run: `bin/check`, `pytest` (no code changed).
- Not verified: matching of plan lines to rows beyond four rows; the generator's placement (an illustration); every claim in "Other apps".
