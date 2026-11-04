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
Migration `20270101090000_k2_page_parts.sql` (additive; renumbered after #374 took 20261231090000): widens `curriculum_proposal.kind` with `page_part`, `material` (the M1-05
ledger carries the drafts, rule 10); the edit trigger now keeps `steps` and `thinking` too. A catalogue item's `home` (class/school) and `unit_value` stay empty and flagged until a person sets them (D-072; never invented). A part with no source row is empty or
older than this table; the upload writes 'school'; a later upload turns a 'drafted' part into 'school', never a 'person' one.

## Baseline (the orchestrator's counts, not re-measured by me)
Sheet non-empty: steps 624, outcomes 578, materials 711, Level 0–3 756/746/746/746. Live K2 (871): objective 543, materials 646,
level_0 742, level_3 745. `engine curriculum k2 <csv>` now prints exact per-part gaps (`k2_gaps.report`, code). Open for the
coordinator: sheet columns W–Z ("L0..L3") and AD–AI "Revised" are other level sets; not used.

## Built (tests first; the first run failed on the missing module)
- `engine/w1_bank/k2_gaps.py` (pure): empties per part; **inconsistencies** = a name and an objective that give number ranges
  and none overlaps ("Number names 11-20" vs "numbers from 6-10"). Flagged to a person; nothing is changed. Other kinds of
  disagreement need a reader's judgement: a model's question later, never auto-applied.
- `k2_upload.py`: column J → `steps` (config `k2_sheet.json`), `mark_school`, the gap report in the command's output. 358 lines.
- Prompt rows, all `active: false` (rule 7): v1 one page a call, v2 batched (the ones to use): `k2_page_draft` (Sonnet 5.5),
  `k2_page_validate` (v1 Opus, v2 Haiku 4.5; another model, never sees the drafter's reason), `k2_materials_split` (Haiku 4.5; a
  quantity the text lacks is null, never guessed; a name must be in the school's text).
- Run commands (UNRUN, tested on scripted replies): `engine curriculum draft --stage S [--limit N] [--dry-run] --by EMAIL` and
  `materials` (same). `--dry-run` prints a forecast from assumed-token config row `k2.drafting` and makes no call; every batch
  prints spend so far and the stage limit; each paid call is committed at once; a budget stop keeps the good pages. Proposals go
  to the M1-05 ledger (`page_part`, `material`); the existing `curriculum apply` writes them, only into parts still empty, marked
  drafted; `revert` empties only what is still the draft's. A page once proposed is not asked for again, even after a revert (orchestrator agreed).
- D-071 (orchestrator, 4 Nov): EVERY draft is written to its empty part, marked drafted; one the checker disagreed with, that the drafter
  flagged or was unsure of also gets `check_me` (a second tag) and heads `k2_draft.review_list` (check_me first, then `map.audit_share` of
  the rest by code). Nothing the school wrote is touched; `revert` works per proposal. `engine eval curriculum_map [--dev]
  [--version N] [--validate-version N]` now spends from stage held_out / dev_eval.
- Edit path (D-073): `k2_review.keep | change | reject` act only on a part marked drafted (the school's words and a person's own are
  refused); each ends with the mark `person` (keep, change) or none (reject), the doubt cleared, who by id in the history.
- Not built: the eval harness and bars for these prompts (`engine eval` for them), the "drafted" chip and keep/change/reject screens,
  planner lines with no activity (the planner tab is not read). Each needs a go; model runs need Nimish's cost approval.

## Cost, redone for Nimish's $25 (4 Nov; Sonnet 5.5 drafts, Haiku 4.5 checks; ESTIMATE, tokens per call assumed, none measured)
Prices per million tokens in/out: Sonnet 5.5 $2/$10, Haiku 4.5 $1/$5, Opus 5.5 $4/$20 (`config.llm.prices`, at ₹88/$).
| Stage | One call per activity | Batched 4 (10 for materials) |
|---|---|---|
| Mapping dev eval, 100 (Sonnet propose + Haiku check) | $1.4 | $1.4 (the map asks one at a time) |
| Mapping held-out score, 427 | $6.0 | $6.0 |
| Page-draft dev eval, 100 | $2.1 | $1.2 |
| Draft 871 pages + retries | $13.7 | $9.0 |
| Check the drafts (Haiku) | $3.9 | $2.1 |
| Split the materials (Haiku) | $2.4 | $1.7 |
| **Total** | **~$29.5, over** | **~$21.4, under** |
**The plan is the batched column** (orchestrator, 4 Nov: batch now, 4 pages a call, 10 for materials; config row `k2.drafting`). Forecast per
stage against its cap (stop at cap less margin): dev eval = map dev $1.4 + page-draft dev $1.2 = $2.6 against $4 (limit $3.75); held-out score $6.0 against $7; drafting + checks + materials $12.8 against the rest; total $21.4 against the
stop at $23. M1-05's Opus validator is left alone (v1); `curriculum_map_validate` v2 on Haiku 4.5 is a new inactive row whose
eval on the 100 dev rows decides whether it may be used; if it misses the D-063 bars: stop and report, not Opus without Nimish.
Hard stop: `llm.campaigns` (cap $25, margin $2, stages dev_eval 4 / held_out 7 / draft: the campaign's), `adapters/llm_budget.py`.
Batching: `w1_bank/k2_batch.py` judges each page of a reply alone, keeps the good, asks again only for the bad (rounds = 2).

## Verified
- `pytest -q tests/test_llm_budget.py tests/test_llm.py tests/test_k2_gaps.py tests/test_bars.py tests/test_loaders.py` → 64 passed (budget tests written first: 9 failed before the code).
- Affected files one by one (bars, eval_command, llm, school_words, settings, map_*, jev, layout, loaders) → all passed.
- `pytest tests/test_k2_draft.py` → 15 passed (import error first, no module yet). `pytest tests/test_k2_batch.py` → 11 passed (written before the module; I did not run them failing). Stage-cap tests: 4 failed before the code, now pass. `bin/check` → 34 passed (after fixing a pyright error and a renamed test in the goal). The 14 affected files in ONE pytest process (foreground) → 134 passed; the earlier silent stop was a background run, most likely ended by the harness (inferred, not proved).
- `engine live rules` needs `--url`; without it it looked for the live database (that was the silence). With `--url` it lists 23
  rules of my new tables not yet in rules.json: to regenerate after #374 merges. NOT done: the 12-shard suite (waits for #374 and
  the renumber), a run on the real tab or on a copy of live.

## Handoff
- In flight: branch m1-11-k2-complete-v1, committed locally, NOT pushed (orchestrator). Wording bar: 30 pages read by the educator.
- Next on a go: dry run of `engine curriculum k2 <csv>`, rehearsal of the migration, the eval harness on the 100 dev pages.
