# M1-11 — K2 version 1 with no gaps

W1, gate N1 (K2 curriculum, beside M1-05). Goal `goals/m1-11-k2-complete-v1.yaml`. Nimish, 4 Nov (relayed, D-071): every K2
page fully filled, the school's text kept and marked 'school', everything an agent drafts marked 'drafted' until a person
keeps, changes or rejects it. **Built so far: structure, loading the steps, the gap report, the prompt rows. No model call
has been made; nothing is pushed beyond the first note.** teacher-os was never attached here: D-063/070/071 are the orchestrator's words.

## The page (rubric = Level 0–3, the sheet's columns P–S, D-051; Easy..Advance is for question difficulty from G1)
| Part | Where | Sheet col | State |
|---|---|---|---|
| objective | `activity.objective`, `activity_objective` | M | existed |
| steps (what to do) | `activity.steps` | J "LESSON PLANS" | **new: the sheet had it, the table did not** |
| thinking (idea, common slips) | `activity.thinking` | none | new, drafted only |
| level 0–3 | `activity.level_0..3` | P–S | existed |
| materials | `activity.materials` text + `material_item`, `activity_material` (item, quantity, unit) | H | catalogue new |
| source of each part | `activity_part_source` (school / drafted / person, proposal, staff id) | — | new |
Migration `20261231090000_k2_page_parts.sql`: additive; widens `curriculum_proposal.kind` with `page_part`, `material` (the M1-05
ledger carries the drafts, rule 10); the edit trigger now keeps `steps` and `thinking` too. A part with no source row is empty or
older than this table; the upload writes 'school'; a later upload turns a 'drafted' part into 'school', never a 'person' one.

## Baseline (the orchestrator's counts from the Activity tab export; not re-measured by me)
Sheet, non-empty: steps 624, outcomes 578, materials 711, Level 0–3 756/746/746/746. Live K2 (871): objective 543, materials 646,
level_0 742, level_3 745, requirement 590, note 78. Exact per-part counts now print from the file `engine curriculum k2 <csv>`
already reads (`k2_gaps.report`, code not a model). Column B has `#REF!` blocks (321 rows without an activity number).
Question for the coordinator: sheet columns W–Z ("L0..L3", headed "Name") and AD–AI "Revised" are other level sets; not used.

## Built (tests first; the first run failed on the missing module)
- `engine/w1_bank/k2_gaps.py` (pure): empties per part; **inconsistencies** = a name and an objective that give number ranges
  and none overlaps ("Number names 11-20" vs "numbers from 6-10"). Flagged to a person; nothing is changed. Other kinds of
  disagreement need a reader's judgement: a model's question later, never auto-applied.
- `k2_upload.py`: column J → `steps` (config `k2_sheet.json`), `mark_school`, the gap report in the command's output. 358 lines.
- Prompt rows, all `active: false` (rule 7): `k2_page_draft` v1 (Sonnet 5.5), `k2_page_validate` v1 (Opus 5.5, low; another
  model, never sees the drafter's reason), `k2_materials_split` v1 (Haiku 4.5; a quantity the text lacks is null, never guessed).
- Not built: the eval and bars for these prompts, the draft/apply commands, the "drafted" chip and keep/change/reject screens,
  planner lines with no activity (the planner tab is not read). Each needs a go; model runs need Nimish's cost approval.

## Cost (estimate; tokens per call assumed, none measured; `config.llm.prices`)
About ₹3,700 (~$42), plan ₹3,000–6,000: draft+retries ~1,210, validate ~1,380, materials ~215, evals on gold ~850. 2–3 hours at
4 calls at once. The inconsistency and planner-only drafts are not sized. Person review is the real cost, unmeasured.
Wording has no automatic bar: the K2 educator reads 30 drafted pages and marks keep/change/reject; counts reported.

## Verified
- `pytest -q tests/test_k2_gaps.py tests/test_k2_upload.py` on a database built by `bin/testdb fresh` + my migration → 25 passed.
- Affected files one by one (bars, eval_command, llm, school_words, settings, map_*, jev, layout, loaders) → all passed.
- `bin/check` → 34 passed. A combined run of those files in one pytest process stopped with no summary (cause not found).
- NOT done: the whole suite in 12 shards; `engine live rules` (no output in 100 s on my database, not diagnosed); a run on
  the real tab or on a copy of live.

## Handoff
- In flight: branch m1-11-k2-complete-v1. Migration and code are committed locally and NOT pushed (orchestrator).
- Next on a go: dry run of `engine curriculum k2 <csv>`, rehearsal of the migration, the eval harness on the 100 dev pages.
