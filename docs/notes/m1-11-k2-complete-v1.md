# M1-11 — K2 version 1 with no gaps: structure, audit, plan, cost (step 1 only)
W1, gate N1 (curriculum for K2; beside M1-05). Nimish, 4 Nov: every K2 activity page fully filled; the school's text kept
exactly; anything an agent drafts is marked "drafted" and a person can change it. **Step 1 only: no model call, no
migration, no code.** Not read: teacher-os (`bin/roadmap card M1-11`, D-063/070/071, curriculum-*.md, tables.md) — the
attach was refused in this session, so the bars below are M1-05's as recorded in this repo, not re-checked against D-063.

## 1. The structure of a K2 activity page (what exists, what is new)
| Part | Where it lives now | Sheet column | New? |
|---|---|---|---|
| objective (the outcomes) | `activity.objective` + `learning_objective` via `activity_objective` | M | no |
| what to do (steps) | **nowhere** | J "LESSON PLANS" | **yes: the sheet has it, we never stored it** |
| how it needs to be thought about (the idea, common slips) | nowhere | none | yes, drafted for all |
| rubric Level 0–3 | `level_0..level_3` | P,Q,R,S "Activity Level 0..3" | no |
| materials | `activity.materials` free text | H "TLMs" | catalogue lines, new |
| skill links | `activity_skill` (source, proposal_id from M1-05) | none | no |
| source of each part, who edits | `curriculum_edit` (who, when) | — | per-part source is new |
Rubric = Level 0–3 as the sheet and D-051 say (orchestrator, 4 Nov); Easy..Advance is question difficulty from G1, not used for K2.
Headers: P="Activity Level 0" (Doesn't sit for the class), Q..S Level 1..3. Unclear: W–AB repeat the levels, AD–AI are "Revised" L0–L4; which set is final.

**Smallest additions (proposal, nothing written):**
1. `activity.steps text`, `activity.thinking text` (two columns, like `materials`).
2. `activity_part_source(tenant_id, activity_code, part, source in ('school','drafted'), proposal_id, edited_by, edited_at)`:
   one row per part, so "drafted" shows on screen and turns to "school/person" when a person edits. Existing trigger already
   writes `curriculum_edit` for the new columns once added to its list.
3. `material_item(code, name, unit)` and `activity_material(activity_code, material_code, quantity)`; free text kept in
   `activity.materials` untouched. Needs the `curriculum_proposal.kind` check widened (migration, additive).
No new ledger: M1-05's `curriculum_proposal` is reused (rule 10).

## 2. Gap audit — what I could and could not measure
- Tab "Activity list_Lesson Plans": 1,429 rows, 44 columns; its first two data rows are fully filled.
- **Per-part empty counts from the sheet: NOT produced.** The connector returns text to the model, not a file, and the
  container cannot download the tab (M0-02). Counting 871 rows × 6 long columns by eye would be a guess, so I did not.
  What I did see: column B (activity no.) has long blocks of `#REF!` and blanks, and Nursery rows sit at the bottom,
  which agrees in kind with the orchestrator's 321 without a number; the count itself is unverified.
- Live (orchestrator's numbers, not mine): of 871, empty = objective 328, materials 225, level_0 129, level_3 126,
  requirement 281, skill link 344. **Steps and thinking were not measured on live because no column holds them.**
- **Two more gap kinds (orchestrator, 4 Nov), to count by code from the CSV:** (a) inconsistencies, e.g. "Number names 11-20"
  whose objective says "numbers from 6-10": flagged to a person, correction proposed and marked drafted beside the school's
  text, never overwriting it (a judgement by model, so never auto-applied). (b) planner lines with no activity row (two FN10
  items seen): the agent drafts an activity, marked drafted. Neither counted yet; the planner tab is not read.
- Exact counts: tab exported as CSV, then a read-only extension of `engine curriculum k2 <csv>`.
## 3. Plan
- **Order:** (a) load steps from column J as "school" (no model; it is the school's text); (b) per-part dry-run counts;
  (c) draft only what is empty, one call per activity returning every missing part; (d) validate; (e) person review.
- **Models (from this repo's prompt rows):** proposer `claude-sonnet-5-5`; validator `claude-opus-5-5` effort low (a
  different model, never shown the proposer's reason). Materials split: Haiku 4.5. The box holds the key; this container has none.
- **Prompts are rows (rule 2):** `k2_page_draft`, `k2_page_validate`, `k2_materials_split`, each inactive until its eval
  meets the bar (rule 7); the school's method is supplied as seed rows, not prose in code.
- **Code decides (a model never does):** every skill/LO code exists in the band and family; materials map to the
  catalogue or are queued as "new item" for a person; a rubric must have four non-identical rungs; school text is never
  overwritten (empty cell only); a drafted part cannot copy another activity's part (word-overlap check).
- **On screen:** a "drafted" chip beside each drafted part (icon plus word, never colour alone); the educator keeps,
  edits (the part becomes person-owned, drafted flag gone, `curriculum_edit` row) or rejects (part returns to empty,
  proposal row says no). Nothing drafted is shown to a parent unreviewed.
- **Bars (proposed, to be set before any run, as M1-05 did):** gold = the 527 activities people filled; objectives and
  rubrics are scored on the dev 100 then held-out 427 for facts code can check (valid codes, four rungs, no copy);
  wording: a person reads 40 per part, bar 90% kept unchanged (my number; Nimish may change it). No automatic test of wording.
## 4. Cost and time — ESTIMATE; tokens per call assumed, none measured
Prices from `config.llm.prices` (₹ per million tokens, in/out): Sonnet 5.5 176/880, Opus 5.5 352/1760, Haiku 4.5 88/440.
| Run | Calls | Tokens in/out per call | ₹ |
|---|---|---|---|
| Draft (871 calls) + 25% repair retries | ~1,090 | 1,800 / 900 | ~1,210 |
| Validate | 871 | 2,500 / 400 | ~1,380 |
| Materials split | 871 | 800 / 400 | ~215 |
| Evals (dev 100 + held-out 427, draft+validate) | ~527 | as above | ~850 |
**Total about ₹3,700 (about $42); plan for ₹3,000–6,000, plus the inconsistency check and planner-only activities (not yet counted).** Time with 4 calls at once, ~25 s per activity: about 1.5 hours
for the run plus about 40 min for evals, so 2–3 hours. Person review is the real cost, unmeasured.
## Unverified / open
- No sheet counts (above). Tokens per call assumed. teacher-os decisions not read. D-051 not read (teacher-os).
- Whether column J holds steps for all 871 (blank J not counted yet). Next on a go: CSV, counts, migration, prompts, eval.
