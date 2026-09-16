# Cornerstone Assessment Engine — spec v0.1 (15 Sep 2026)

Scope: the "tested" evidence channel (Learning OS Part 2c) for G1–G4 Maths, built first on the addition/subtraction strand. Objective → item bank → per-level worksheets → paper → photo → per-item results → evidence log → next worksheet. n8n orchestrates; it does not think.

Status: draft for Aseem + Nimish review. Nothing here is ratified. Skill IDs mapped against the Skill Map registry data (built 15 Sep 2026; 244 skills, 849 milestones). Reviewed page: claude.ai/artifact/2ubdvYwB1HtQcY4qKzb5yT

---

## 0. What this changes from the brief

| You asked for | This spec does instead | Why |
|---|---|---|
| Three invented levels (basic / intermediate / advanced) per objective | Levels = **rungs on the strand ladder**, pinned to spine milestones: `below band / at band / above band` for the class's grade | A parallel level vocabulary recreates the three-unreconciled-taxonomies failure the Drive audit found. Results must land on the ladder or the child graph can't use them. |
| Engine generates *assignments* on demand (N questions × M variations) | Engine generates *items* into a reviewed, versioned bank; worksheets are **assembled** from approved items by a deterministic picker | Review cost is paid once per item, not once per sheet. Variations become free and provably non-overlapping. Bad items retire permanently. Item statistics accumulate. |
| One prompt creates the questions | Procedural items come from **parameterised generators** (exact arithmetic, zero LLM); the LLM writes only contexts, explain-items and find-the-mistake items, and every LLM output is re-checked by code | LLM arithmetic errors on a school worksheet are unacceptable, and the generator also pre-computes the *wrong* answers each misconception would produce — which is what makes marking diagnostic instead of just right/wrong. |
| Photo → Claude figures out the mistakes | Worksheet is designed for the camera first (QR, fiducials, digit cells); closed items are marked by **lookup**, not by a model; the vision model only reads digits in known boxes | Reliability. Diagnosis of a wrong numeric answer is arithmetic against the misconception table, not inference. |
| Per-child sheets from day one | v1 = three level-variants per class, teacher assigns; per-child assignment arrives when the graph exists (Phase 2–3) | No per-child skill estimates exist yet. Also a real print/collation cost — see §6. |
| n8n as the engine | n8n as the **control plane**: triggers, Sheets/Drive I/O, human-approval waits, notifications, retries. Generation, validation, selection, rendering, marking live in code n8n calls | Prompts and logic inside n8n nodes can't be diffed, tested or reviewed. You'd end up with one giant Code node. |

---

## 1. The strand ladder: addition & subtraction, G1–G4

Built from the Drive evidence (Maths pedagogy pack by Neha S, Cornerstone Syllabus Grade 1, Cambridge G1 topic plans, Assessment 1 / Set B diagnostics and answer keys, the G4 "Diagnostic Ladder" L1–L8, the G3 5-level subtraction ladder). Each rung is a candidate **milestone** in the spine. The `skill_id` column is empty on purpose — I don't have `skills.csv` in this project; reconcile before anything is tagged (§12).

| Rung | Band | Descriptor (what the child can do) | Drive evidence | Generator family | Machine-markable |
|---|---|---|---|---|---|
| R1 | G1 | Adds within 10 by combining two sets; reads and writes `+` and `=` | Cambridge G1 topic 8 "Addition as Combining"; G1 doc "if the child doesn't understand the symbol, remove the symbol" | `ADD.W10` (pictorial sets + numerals) | Yes (numeral answer) |
| R2 | G1 | Adds within 20 using ten-frame / part-part-whole; knows +1, +10 patterns | G1 doc: ten frame, part-part-whole, "what happens when we add 1?" | `ADD.W20`, `PPW.W20` (missing part) | Yes |
| R3 | G1 | Subtracts within 20 as take-away *and* as "how many more"; counts up on a number line | G1 doc: Take Away, 1:1 matching, Cross Out, count-up; Cambridge topic 9 | `SUB.W20.TAKE`, `SUB.W20.DIFF` | Yes |
| R4 | G1→G2 | 2-digit ± **without** regrouping in place-value columns | G2 diagnostic "with and without carrying"; G4 ladder L4 | `ADD.2D.REG0`, `SUB.2D.REG0` | Yes |
| R5 | G2 | 2-digit addition with **one** regrouping (34+28) | G2 doc; Short Assessment 47+38, 56+29 | `ADD.2D.REG1` | Yes |
| R6 | G2 | 2-digit subtraction with exchange (52−28); school vocabulary is "exchange/regroup", not "borrow" | G2 doc ("I would avoid the word borrow"); Short Assessment 62−27, 81−45 | `SUB.2D.REG1` | Yes |
| R7 | G2 | Mental strategy: friendly numbers / compensation (38+22 → 40+20; 52−19 → 52−20+1) | G2 doc "Which is easier?" | `MENTAL.COMP` (answer + strategy choice) | Answer yes; strategy = human/LLM-assisted |
| R8 | G2→G3 | One- and two-step word problems in ₹ / objects; read-aloud permitted | G2 shop ₹15/₹28/₹12; diagnostic word problems; Set B "Applied" band | `WP.1STEP`, `WP.2STEP` (LLM context, code-checked numbers) | Numeric answer yes; working = human |
| R9 | G3 | 3-digit ± with regrouping, incl. two regroupings (246+375; 625−278) | G3 doc; "increase only one difficulty at a time" | `ADD.3D.REG{1,2}`, `SUB.3D.REG{1,2}` | Yes |
| R10 | G3 | Subtraction **across zero** (700−198; 302−178) | G3 doc; Set B answer key "error borrowing across the zero" | `SUB.3D.ZERO` | Yes |
| R11 | G3 | Estimates first (round to 10), judges reasonableness (602−298 ≈ 300) | G3 doc estimation-first; diagnostic rounding | `EST.R10` (two answers: estimate + exact) | Yes |
| R12 | G4 | 4-digit addition with multiple addends; 4-digit subtraction across zeros (2,450+3,275+1,850+1,425; 5,000−3,275) | G4 doc School Budget, Travel Distance | `ADD.4D.MULTI`, `SUB.4D.ZERO` | Yes |
| R13 | G4 | Chooses an efficient strategy and justifies it (4,999+2,998; 5,000−1,998) | G4 doc "Which method would YOU use?" | `STRAT.CHOICE` | Answer yes; justification = human/LLM-assisted |
| R14 | G4 | Multi-step ₹ problems under a constraint (plan within ₹30,000) | G4 School Trip Planner | `WP.MULTI.BUDGET` | Partial (numeric parts yes) |
| X1 | G2+ | **Explains** the procedure (why the extra ten moves column) | Set B "Conceptual Understanding" block; answer-key acceptance criteria | `EXPLAIN.*` (LLM-drafted stem, rubric from answer key) | No — teacher marks with rubric assist |
| X2 | G2+ | **Find the mistake** in a worked example (a planted misconception) | Set B find-the-mistake; diagnostics G3/G4 | `FTM.*` (generator plants a specific misconception) | Yes — the *which mistake* is closed; the explanation is open |


### 1.1 Rung → registry mapping

| Rung | Skill IDs | Registry milestone / LOs | Verdict |
|---|---|---|---|
| R1–R2 | NUM.OPS.01 | G1 Dev Update: "Addition through Number Line - 20 / quantities / counters / **2 digits Addition with carrying**"; LO-G1-0007, -0009, -0013 | First three clauses fine; fourth is R5 content (conflict below) |
| R3 | NUM.OPS.02 | G1: "Number Line - 10 / 2-digit without borrowing"; LO-G1-0008, -0010 | Align "10" to 20 |
| R4–R6 | NUM.OPS.01, NUM.OPS.02 | G2 report items: "3 digits addition with carrying"; "2 digits subtraction without / with borrowing"; LO-G1-0011 (2-digit ± with/without regrouping **at G1**), LO-G2-0487, -0489 | **Placement conflict**: syllabus + report card put 2-digit regrouping at G1 and 3-digit at G2; Neha's pack + July diagnostic put 2-digit regrouping at G2 (borrowing = G2 stretch), 3-digit at G3. Engine unaffected (assigns by rung); report card is scoring G2 on 3-digit while class is taught 2-digit. Founders pick one band label per rung. |
| R7 | NUM.OPS.05 | G2: number bonds, counting on/back, bridging 10/100; LO-G2-0488, -0491 | Matches |
| R8 | NUM.PRB.02, NUM.MEAS.04 | G2 "Concept of word problems"; money LOs; LO-G2-0490, -0538, -0558 | Matches; tag both skills |
| R9–R10 | NUM.OPS.02 (and .01) | G3 subtraction milestone **identical to G2**; LO-G3-0938 "strategies" | **Gap**: 3-digit subtraction and across-zero absent from registry though taught (G3 pack) and tested (Set B 625−278, 700−198, 302−178). Add two G3 milestones. |
| R11 | NUM.PV.03, NUM.PRB.03 | Round to 10/100; "Estimate and check answers"; LO-G2-0559, LO-G3-0988 | Matches |
| R12–R14 | NUM.OPS.01/.02, NUM.PRB.02, NUM.MEAS.04 | G4: one line "Addition & subtraction strategies (mental/written)"; LO-G4-1334/1335, -1364, -1365 | **Gap**: no G4 content ladder. R12–R14 (from the G4 pack) should become milestones. |
| X1–X2 | NUM.PRB.03 | desc already names "explains thinking… find-the-mistake"; LO-G2-0561, LO-G3-0990 | Matches; tag PRB.03 plus the rung interrogated |

**Proposed registry v1.1 changes** (Akanksha ratifies at Saturday sync): (1) replace the coarse NUM.OPS.01/.02 milestone rows with R1–R14 as milestones carrying rung_id; (2) one band label per rung — recommend *taught-in* (Neha's pack, confirmed by the diagnostic) with syllabus band kept as *expected-by*; (3) add G3 milestones for 3-digit and across-zero subtraction and G4 content milestones; (4) move LO-G3-0939 / LO-G4-1336 "Generalising odd & even" off Addition onto NUM.CNT.11.

**Data bugs found**: all G4 LOs in this strand tagged signal = Foundational (LO-G4-1334…1387) — a tagging default; text corruption "chVisual artss" (LO-G4-1383), "pVisual artsitioning" (LO-G4-1327) from a global art→Visual arts replace; activity links for NUM.OPS.01/.02 exist only at K2.

Cross-cutting rules that come straight from your existing diagnostics:
- Every sheet carries **one Foundational item from the rung below** (their "Foundational Check"). Your own decision rules ("wrong on foundational + wrong at-grade → foundational gap") depend on that item existing.
- Every computation item has a **working box** separate from the answer box. The Set B scoring note — "a correct answer with no working and a correct answer with clearly shown reasoning are different signals" — becomes a field: `working_shown ∈ {none, partial, full}`, read by the vision model, confirmed by the teacher.

Ladder caveat: rungs are drawn from teaching docs, not from an assessment standard. Neha, Aseem and the Grade 2/3 teachers should look at R4–R11 specifically — that is where the pilot lives and where the boundaries matter most.

---

## 2. Level rule

For a class in grade *g* on strand *S*:

- **L−** = the rung immediately below the grade band's at-band rung(s)
- **L0** = the at-band rung(s)
- **L+** = the rung immediately above

Example, Grade 2, addition/subtraction: L− = R4, L0 = R5 + R6, L+ = R7 (or R9 for the strongest group). A child flagged "foundational gap" on the diagnostic gets R3 as their L−.

Rules:
1. A worksheet variant targets exactly one **primary rung** and is labelled by it — never by a free-text difficulty label.
2. Every item stores `skill_id` **and** `rung_id`; every result lands in the evidence log at that rung.
3. The three variants of one objective share the same `skill_id`, so results across the class are comparable on one ladder.
4. Levels are a property of the *sheet*, not of the *child*. The child's position is derived from results, never written by a person into the sheet-assignment step.

---

## 3. Objects and the Google Sheets schema

One workbook, `Assessment Engine`, tabs below. Sheets is the review surface and the v1 store; migrate to Supabase when a second class joins (your existing rule). Column names are proposals — align them with whatever `skills.csv` already uses.

**`skills`** (read-only mirror of the spine) — `skill_id · domain · strand · subject · topic · name · primary_pillar · spine_version`

**`rungs`** — `rung_id · skill_id · band · order · descriptor · milestone_id (spine) · drive_source`

**`item_templates`** — `template_id · skill_id · rung_id · signal (Foundational|Conceptual|Procedural|Application|Stretch) · format (vertical|horizontal|missing_part|word|explain|find_mistake|estimate) · constraints_json · render_template · answer_expr · misconception_map_json · language · status · owner`

**`items`** — `item_id · template_id · skill_id · rung_id · signal · format · language · stem · options_json · answer · answer_type (int|two_ints|choice|open) · misconception_answers_json · working_lines · source (generator|llm|teacher) · prompt_id · prompt_version · spine_version · status (draft|approved|rejected|retired) · reviewed_by · reviewed_at · reject_reason · times_used · p_correct · last_used_at`

**`blueprints`** — `blueprint_id · rung_id · n_items · signal_mix_json · formats_json · foundational_from_rung · notes`

**`sheets`** — `sheet_id · objective_id · skill_id · rung_id · level (L-|L0|L+) · variant · class · child_id (nullable in v1) · blueprint_id · item_ids_json · answer_key_json · rng_seed · pdf_url · created_by · created_at · printed_at`

**`sheet_items`** — `sheet_id · position · item_id · answer_box_geometry_json · working_box_geometry_json` (geometry in mm from the page origin; written by the renderer, read by the marker)

**`item_results`** — `result_id · sheet_id · child_id · position · item_id · raw_read · read_confidence · working_shown · correct (Y|P|N|blank) · misconception_ids_json · confirmed_by · confirmed_at · photo_ref`

**`evidence_events`** — the shared log from the child-graph doc; this engine writes rows with `source = item`.

**`prompts`** — `prompt_id · version · purpose · text · model · created_at · created_by`. n8n fetches prompts by ID at runtime. Prompts are never edited inside n8n.

**`misconceptions`** — `misconception_id · strand · name · description · predicted_answer_fn · repair_hint · source (teacher_list|tutor_spec|observed)`. Seed from Neha's teacher-authored list and the tutor-engine spec's M001–M010; make it the shared vocabulary now, not later.

---

## 4. Item generation — where the LLM is and isn't

### 4.1 Procedural items: generators, not prompts

A template is a small parameter spec. Example:

```
template_id: ADD.2D.REG1
skill_id: <NUM.OPS.? — reconcile>
rung_id: R5
signal: Procedural
format: vertical
constraints:
  a: 10..99
  b: 10..99
  ones_sum: ">= 10"        # forces exactly one regrouping
  tens_sum_with_carry: "<= 9"   # forbids a second
  exclude: [a == b, b < 10]
answer_expr: a + b
misconception_map:
  M_NOCARRY:      (a%10 + b%10)%10 + 10*((a//10)+(b//10))       # 47+38 → 75
  M_CARRY_TO_100: (a%10 + b%10)%10 + 10*((a//10)+(b//10)) + 100  # 47+38 → 175
  M_CONCAT_ONES:  concat(tens_sum, ones_sum)                     # 47+38 → 715
  M_FACT_PM1:     answer ± 1, answer ± 10
render: vertical(a, b, '+')
working_lines: 3
```

The generator samples under constraints, computes the exact answer, computes every predicted wrong answer, and rejects any item where two misconceptions collide on the same wrong answer (or stores both — see §9). Hundreds of items per template, zero arithmetic risk, no review of the arithmetic needed — review is of the *template*, once.

Seed the misconception list from Neha's own notes (verbatim from the Drive): forgets to carry; carry placed in the wrong column ("if carry at tens place they do at hundreds"); fact off-by-one ("5+3 → 7 or 9"); drops the hundred ("76+54 → 30 instead of 130"); subtracts the smaller digit from the larger regardless of position ("neeche wala number"); exchange errors; across-zero errors. Reconcile with M001–M010 from the tutor-engine spec — I have not seen that list in full and won't guess its contents.

### 4.2 LLM items: contexts, explanations, planted mistakes

The LLM is used for exactly three things:
1. **Word-problem contexts** around numbers the generator already chose (Indian, age-appropriate, ₹, names varied, EN/HI/MR). The numbers and answer are inputs to the prompt, not outputs.
2. **Explain-items** (X1) with a rubric drafted from your Set B answer-key acceptance language ("accept any explanation showing the extra ten moves to the next column").
3. **Find-the-mistake items** (X2): the generator plants a specific misconception into a worked example; the LLM writes the child-friendly framing.

Prompt contract (every LLM call):
- Receives the rung descriptor **verbatim**, the exact numbers, the target signal and format, grade word-count cap, and forbidden vocabulary ("borrow").
- Is told it may not change the numbers or invent objectives.
- Returns strict JSON (structured output): `stem, answer, answer_type, options?, rubric?, reading_words`.
- Output goes through the **validator** (§8) before it can be written as `draft`.

### 4.3 Bank size for the pilot
One rung ≈ 40–60 approved items across signals (matches your Phase 1b number). Procedural items are effectively unlimited from the generator; the review bottleneck is LLM items only. Budget review at ~30 seconds per LLM item.

---

## 5. Blueprint-driven assembly (why variants must be *equivalent*, not just different)

If variant A and variant B of the same L0 sheet differ in signal mix or operand difficulty, the child who got B looks worse than the child who got A and you've written noise into the graph. So a sheet is assembled from a **blueprint**, and all variants of a level satisfy the same blueprint.

Example blueprint, G2 L0, 7 items:
```
foundational_from_rung: R4     → 1 item
Conceptual (R5/R6, missing_part or pictorial)   → 1
Procedural R5 (ADD.2D.REG1, vertical)           → 2
Procedural R6 (SUB.2D.REG1, vertical)           → 2
Application R8 (WP.1STEP, ₹)                   → 1
```
A 5-item sheet drops one Procedural and the Conceptual; a 10-item sheet adds one X2 find-the-mistake, one R7 mental item, and one more of each Procedural. Teacher picks 5/7/10 and variant count; the picker does the rest.

Picker rules (deterministic, seeded by `sheet_id`):
1. Fill each blueprint slot from `status = approved` items at the slot's rung/signal/format.
2. No item repeats across variants of the same objective unless the pool is exhausted (then log it).
3. **Exposure**: an item a child saw in the last 21 days is excluded for that child (v1: for that class). 21 days is my number — calibrate.
4. Operand-difficulty balance across variants: same count of regroupings, operand magnitude within a band. Log a warning if any variant drifts.
5. Write `sheets` + `sheet_items` before rendering, so a render failure never leaves an unrecorded sheet in circulation.

---

## 6. The worksheet template — designed for the camera

This is the piece to hand-build and photograph **before** any code (§10, week 0). Requirements:

- A4 portrait, Cornerstone header. I have not read the Brand Book in this session; this section covers structure and machine-readability, not brand application.
- Header row: school mark · **Name (pre-printed when child_id known; else a roll-number box of 2 digit cells)** · Class · Date · "Today I am practising: ___" in child language.
- **QR code** top-right encoding `sheet_id` only (no child data in the code); a 6-character human-readable code beside it in case the QR is smudged or cut off.
- **Four fiducial squares** at the page corners for perspective correction from a phone held at an angle.
- Each item in a fixed-height numbered block: stem on the left; **working box** (ruled, 3 lines) below the stem; **answer box** as a row of digit cells (one digit per cell, count = max answer length + 1) on the right. Digit cells are what make 7-year-old handwriting readable by a model.
- No item crosses a page boundary; item positions are fixed by the renderer and written to `sheet_items.answer_box_geometry_json`.
- Open items (X1) get a lined box and are never machine-marked.
- Footer: "Drafted by system · reviewed by ___ on ___" — your existing convention — plus `sheet_id`.
- Rendering: HTML → PDF (headless Chromium) via a small service, **not** Google Docs templating. Reason: the marker crops answer boxes by coordinates, so the renderer must control geometry to the millimetre. Docs/Slides templating cannot.
- Print output: one merged PDF per class **in handout order** (roll order, level interleaved), so the teacher gets one stack, not three piles. This is the difference between "differentiated worksheets" and "a teacher sorting paper for ten minutes".

---

## 7. The n8n flows

Three flows, all following your rule: *trigger → step with versioned prompt → human confirm → write*. Node types are the standard n8n ones as I know them — Form Trigger, Schedule Trigger, Google Sheets, Google Drive, HTTP Request, Code, IF/Switch, Loop Over Items, Merge, Wait, Gmail/WhatsApp send, plus the LangChain-style LLM chain and structured-output nodes. **n8n renames and reorganises nodes across versions and you don't have an instance yet; verify every node name against your installed version before building. Don't treat mine as authoritative.**

### Flow A — Build the item bank (human-gated; runs when a rung is queued)

1. **Trigger**: n8n Form — `rung_id`, target counts per signal, languages, requester.
2. **Google Sheets: read** `rungs` + `skills` rows → descriptor, band, skill_id, spine_version.
3. **Google Sheets: read** `item_templates` where `rung_id` matches and `status = active`.
4. **HTTP Request → generator service** `/generate` with templates + counts → procedural items, each with exact answer and misconception answer table.
5. **Google Sheets: read** `prompts` for the three LLM purposes (latest version).
6. **Loop Over Items → LLM chain (structured output)** for word / explain / find-the-mistake slots only. Inputs: rung descriptor verbatim, generator-chosen numbers, grade caps.
7. **HTTP Request → validator** `/validate` on every LLM item (§8). Pass/fail with reasons.
8. **IF fail → one retry with the reason appended → else drop and count.**
9. **Merge** generator + surviving LLM items → **Google Sheets: append** to `items` with `status = draft`, `prompt_id/version`, `spine_version`.
10. **Notify** reviewer: "N items at draft for R5 — review sheet link." **Flow ends.** Nothing at `draft` can ever be printed.

Review is a human changing `status` to `approved` or `rejected` (+ reason) in the sheet. n8n doesn't do the reviewing.

### Flow B — Assemble and print worksheets (the everyday flow)

1. **Trigger**: n8n Form — objective (`skill_id`), class, date, items per sheet (5/7/10), variants per level, assignment mode (`class-3-levels` in v1; `per-child` later).
2. **Google Sheets: read** approved items for the skill's L−/L0/L+ rungs; read `blueprints`; read `sheets` (last 21 days, this class) for exposure.
3. **HTTP Request → picker** `/assemble` → for each level × variant: item list, answer key, seed. (Could be a Code node; keep it a service so it's tested.)
4. **Google Sheets: append** `sheets` and `sheet_items`.
5. **HTTP Request → renderer** `/render` → PDFs + box geometry; **Google Sheets: update** `sheet_items` geometry.
6. **Google Drive: upload** individual PDFs + one merged handout-order PDF to `/Assessments/<class>/<date>/`.
7. **Notify** teacher with the merged PDF link and the answer-key link (coordinator only).

### Flow C — Mark back and write evidence

1. **Trigger**: Google Drive folder watch (v1) — teacher drops photos into `/Assessments/<class>/<date>/scans/`. WhatsApp inbound later (Cloud API approval timeline unknown; also a DPDP surface — photos carry children's names).
2. **HTTP Request → preprocess** `/deskew` → perspective-correct via fiducials, decode QR → `sheet_id`, crop each answer box and working box by stored geometry. Unreadable QR → route to a "manual match" queue with the 6-char code visible.
3. **Loop Over Items → vision model** on each *answer-box crop*: returns digits + confidence, and `working_shown ∈ {none, partial, full}` from the working crop. Small crops + digit cells = high accuracy; measure it in week 0 — I have no figure for 7-year-old handwriting and won't invent one.
4. **Code: mark** — closed items: compare to `answer_key`; if wrong, look up `misconception_answers_json` → `misconception_ids`. **No model in this step.**
5. **IF** `read_confidence < threshold` or `answer_type = open` → **review queue** (a Sheet tab the teacher confirms from; target < 2 minutes per class). Open items get an LLM rubric-assist suggestion, never an auto-mark.
6. **On confirm** (Sheets row edited, or n8n Wait-for-webhook): **append** `item_results` and `evidence_events` (`source = item`, `skill_id`, `rung_id`, `correct`, `misconception_ids`, `sheet_id`, `spine_version`, `confirmed_by`).
7. **Code: estimate** per child × rung — proportion correct, recency-weighted (your stated v1 estimator). Write to a `child_rung_estimate` tab.
8. **Notify** teacher card: "R5: 4 secure, 3 show *forgets to carry* twice → reteach group; 2 ready for R7." Drafted by system, confirmed by teacher before anything moves to a parent lens.

### What must not live in n8n
Prompts · item templates and constraint logic · the picker · the renderer · the answer-key and misconception tables · the marking rules. n8n holds triggers, credentials, sequencing, waits, Sheets/Drive I/O, notifications, error handling. If you find logic creeping into a Code node, move it to the service.

Hosting note, not a certainty: children's names and work photos will pass through this. Self-hosting n8n keeps that traffic on infrastructure you control, which is easier to defend under DPDP than a third-party cloud instance. Verify with whoever signs the data register.

---

## 8. QA gates (what "validated" means)

1. **Arithmetic recompute** — 100% of numeric items, by a checker independent of the generator and of the LLM.
2. **Constraint conformance** — the item actually exercises the rung. A "one regrouping" item with zero regroupings is a silent, common failure; check it explicitly.
3. **Duplicate detection** — normalised hash of numbers + format within a rung; near-duplicate check across the word-problem stems.
4. **Reading load** — word-count cap by grade; forbidden vocabulary list ("borrow"); names drawn from a Cornerstone-approved list (the Set B sheet has a name/pronoun mismatch — "Akanksha… Is he correct?" — this class of error is cheap to prevent).
5. **Human approval** — nothing prints at `draft`. Reviewer sees item, answer, misconception table, and the rung descriptor side by side.
6. **Blueprint equivalence** — variants of a level must have identical signal mix and balanced operand difficulty; the picker refuses otherwise.
7. **Post-hoc item statistics** — after ~30 results, flag any item with `p_correct` below ~0.2 or above ~0.95 at its intended rung as mis-levelled. These thresholds are my suggestion, not a standard; calibrate on your data.
8. **Marking agreement** — your existing gate: ≥ 95% agreement with the teacher on closed items before the pipeline's marks are trusted.

---

## 9. What the loop actually tells you (and what it can't)

- A wrong numeric answer that matches a misconception's predicted answer is tagged with that misconception **by lookup**. Two misconceptions can collide on the same wrong answer (e.g. "smaller-from-larger" and "exchange without decrementing tens" can both yield 45 for 62−27); the tag is then a set, and the working box (read at lower confidence) or the teacher's 1:1 resolves it. Store the set; don't force one.
- A wrong answer that matches nothing is `unclassified` — those are the interesting ones and feed the misconception list.
- Blank vs wrong vs wrong-with-working are three different signals in your own diagnostic decision rules; keep them as three values, never collapse to "incorrect".
- **Next-sheet rule, v1** (thresholds mine, calibrate): at-band rung ≥ 80% correct over the last two sheets with no repeated misconception → next sheet is L+; < 50% or the same misconception on two sheets → L− and a targeted mini-set on that misconception; else stay. Teacher can override; the override is itself an evidence event with a reason.

---

## 10. Build order

**Week 0 — paper, no code.** Pick the rung (R5+R6 for a G2 class). Hand-write one 7-item sheet per level in the §6 template. Print. Run in one class. Teachers photograph from their own phones in normal classroom light. Test: can the QR be read, can the digit cells be read by the vision model, can a human map every scribble to an item. This afternoon's work de-risks everything downstream. If the template fails here, nothing else matters.

**Week 1 — generator + validator + 60 items.** Templates for R4–R7 as code with tests. Generate; LLM items for R8 and X2; Aseem reviews in the sheet. Measure review minutes per item.

**Week 2 — picker + renderer + one real cycle.** 3 levels × 2 variants, 7 items. Print in handout order. Run in class. Collect.

**Week 3 — marking on the collected sheets.** Preprocess, read, mark, review queue. Measure agreement against the teacher's own marking. Write evidence events. Produce the first teacher card.

**Week 4 — wire into n8n.** Only now. n8n earns its place when the trigger is a form a coordinator fills without you, and when Flow C runs unattended on a folder. Before that it's overhead.

Gates before a second rung or a second class: agreement ≥ 95% on closed items; teacher confirms the card is useful; review minutes per item known.

---

## 11. Open decisions (need a human)

1. **Who approves generated items before they print** — Aseem, Neha, or the grade's Maths teacher? One named person per subject; their approval moves an item from `draft` to `approved`. Their throughput is the rate limiter, not generation.
2. **Registry v1.1** — accept the four changes in §1.1?
2. **Languages for v1** — Maths in English only, or EN + HI stems from the start?
3. **Child ID on the sheet** — pre-printed name (needs assignment before printing) vs roll-number digit cells (child writes). I'd pre-print in v1 with class-level assignment; it's the same PDF per level with a different header.
4. **Photo channel** — Drive folder (v1) vs WhatsApp Cloud API (approval timeline and DPDP surface unknown).
5. **Adopt the misconception vocabulary now** — merge Neha's list and M001–M010 into one `misconceptions` tab owned by the Maths lead.
6. **Consent text** — item results and work photos are children's personal data; the purpose register and parent note from the Learning OS doc must cover this channel before week 2's class run.
7. **Hosting** — n8n Cloud vs self-host (see §7 note).

---

## 12. Uncertainty register (read this before quoting anything above)

- **Registry read from the Skill Map artifact data (`window.CSMAP`), not a canonical skills.csv.** IDs hold; if Akanksha edited the sheet after 15 Sep, milestone text may have moved. Re-run reconciliation against the live sheet before tagging real results.
- **The rung ladder (§1)** is inferred from teaching docs and diagnostics in the Drive audit, not from the registry or a published standard. Boundaries R4–R11 need the Grade 2/3 teachers' eyes.
- **n8n node names** — unverified against any installed version; treat §7 as flow logic, not as a build sheet.
- **Vision accuracy on children's handwriting in digit cells** — no measured figure; measure in week 0.
- **Thresholds** — 21-day exposure, 0.2/0.95 item flags, 80%/50% promotion rules, < 2 min review target — all mine, none standard. The 95% agreement gate and 40–60 items are yours.
- **Brand application** — Brand Book not read this session; §6 is structural only.
- **WhatsApp Cloud API approval timelines** and **DPDP treatment of work photos** — not verified; both are lawyer/vendor questions, not design questions.
- **M001–M010 contents** — the "Tutor Engine, Placed" page is a *review* of the Adaptive Subtraction Learning Engine spec; the spec itself was an upload in that session and is not in the project. Add the source spec to the project to seed the misconception tab from it.
