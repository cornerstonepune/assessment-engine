# Assessment Workflow — design v1 (16 Sep 2026)

Readable page: claude.ai/artifact/7vLHpTKuLV1jpsvEduea8e (use that, not this file). Companion to `design/assessment-engine-spec-v0.1.md` (the engine internals) and the prototype build (catalogue: claude.ai/artifact/EA6CjXzLZYo8fyo1WQ3cpk). No code written for the workflow yet — by instruction.

## Sources
NeoSapien recordings 16 Sep 13:57–15:05 (Aseem, Achal; four sub-minute clips ignored); `cornerstone/khare` sheet (Achal: year plan by month × grade, maths periods, Smart/Average/Weak grouping, Khare topic checklist per child); Drive folder 1A3vNmSQUFDSTXH30HyMZUAUwERwO2Val (G2: 11 child folders, Sept 1st/2nd PDFs; G3: 5 child folders, Assessment 0 photos + typed parent summaries — the Kabir summary is misconception-based and is the target shape of the parent output).

## What was agreed on the day (Aseem/Achal/Nimish)
Maths first. Skills in objective terms — Neha & Achal write the skill sets per topic ("addition → ~8 sets"); Easy/Medium/Hard/Advance per set; push the top, focus below the objective. Week: Mon–Wed teach, Thu guided differentiated practice, Fri differentiated assessment, home engagement after. Question bank (~50/skill/difficulty), five different sheets per group, no repeats per child. System marks; teacher tells the system what was taught, reviews, approves ("everything approved by the teacher"). QR on every sheet ↔ exact items; named sheets prescribed per child + unnamed spares per difficulty; photos back; next class the child gets the next named sheet. Outputs: gaps skill-wise → what to practise → which sheet → child trend, class trend, parent summary; Phase 3 teacher effectiveness. Deterministic core; LLM sparingly. Differentiated *learning*/timetable problem parked (second-degree).

## The twelve nodes
| # | Node | When | Inputs | Does (who) | Outputs |
|---|---|---|---|---|---|
| N1 | Skill sets & ladder | per topic, versioned | registry; Neha/Achal breakdown (sets, can-do, E/M/H/A operand rules, example, mistakes) | code + Aseem ratifies | skill_sets, rungs, difficulty_bands, misconceptions; registry proposals |
| N2 | Question bank | on N1 change; nightly top-up | templates; context bank; prompts | code (LLM for sentences only); templates approved once | items with keys + misconception tables |
| N3 | Roster & seed state | once | roster; grouping (fallback); **~34 historical assessments** | code + LLM reads old sheets → candidates → teachers confirm in one sitting | children; evidence(source=import); child_skill_state — the first graph |
| N4 | Week declaration | Wed eve / by Thu 7am | teacher voice note or 5-line form; month plan default; mastery-suggested mixed bag; attendance | LLM structures, teacher confirms | week_declaration |
| N5 | Prescribe per child | Thu/Fri 7am | declaration; child_skill_state; exposure; blueprints | code (six-state rules) | prescriptions (named) + unnamed spares; one-line reasons |
| N6 | Build packs | Thu/Fri 7am | prescriptions; items | code | sheets, geometry, keys; pack PDF in handout order + teacher key page |
| N7 | Teacher approves | Thu/Fri morning, <3 min | pack, key, reasons | Achal: tap or reply-edit; pack-level | approved_by; overrides; print |
| N8 | Capture | same day | phone photos (Drive folder v1 / WhatsApp v2); sheets; roster | code: corners → straighten → QR → child; roster name-match for spares | scans; missing list |
| N9 | Mark & diagnose | minutes after | page, geometry, key | code lookup; vision reads digits; confirm queue <2 min | item_results with tags + confidence; agreement vs teacher (first weeks) |
| N10 | Evidence & state | nightly + on confirm | confirmed results; thresholds table | code | evidence_events; child_skill_state (six states); khare checklist filled |
| N11 | Cards & home sheet | Fri evening | state; overrides; home blueprint | code; LLM one sentence/child; Achal confirms | class card; home pack + parent note; next week's seed |
| N12 | Reports & planning | monthly; before a topic | state history; month plan; Kabir-format | code; LLM narrative; coordinator approves | parent reports; class trend; revisit sets; regrouping; "not ready" flags |

## Classroom contract
Folder = named sheets in roll order + 3–4 unnamed spares per difficulty + one teacher key page. Finish early → next-up spare named on the key, child writes name. Absent → sheet stays, system carries it forward. Wrong sheet to wrong child → QR is truth, one tap resolves. After: one pile, photograph, upload. Every printed page has a QR; child identity can be recovered later, sheet identity is never left to a person. Teacher never decides who gets what, never marks, never sees a level in front of a child.

## Weekly teacher load
One voice note, two taps, two photo sessions, one card confirm, ~10 minutes of queue.

## Decisions open
Silence = approval? (proposed yes for practice, no for assessment) · unnamed sheets: name line + roster match (proposed) · approval surface WhatsApp v1 · parent-note consent text owner/date · history confirm sitting: everything once (proposed) · Grade 1 not in first two weeks · second teacher (Neha) declares the same way.

## Build order
Phase 1 (2 wks): N3 history import + confirm → N1/N2 → N4 form → N5 → N6 (named + spares + key) → N7 WhatsApp → N8 Drive → N9 → N10 → N11 card. Gate: ≥95% marking agreement; card changed a Monday. Phase 2 (4 wks): voice declaration, home sheets + parent note, parent reports, G1 import. Phase 3: effectiveness, computed regrouping, G1 template, second teacher, fractions.

## Draft skill sets for Neha & Achal (to correct, not write)
Multiplication MUL.1–6 (equal groups; tables recall; multiples & factors; 2-digit × 1-digit with the partial-product carry mistake from Kabir's summary; word problems; doubling/halving). Fractions FRA.1–5 (part of whole; fraction of quantity; number line; compare/order; add/subtract same denominator). Each with E/M/H/A operand rules and known mistakes — on the page.
