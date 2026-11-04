# M1-16 brick 2: a person clears a waiting note, and approves words and units (W2, step N4)

One migration (`20270105090000_materials_review.sql`, additive, runs twice). No model call is made or needed.

## What it does, in the school's terms
- A note the system could not confirm waits (`materials_note_review`). The coordinator can **put it on the class's list** (through
  `materials_list.add`, so a cleared note is a line like any other and every rule of a line holds) or **set it aside with a reason**.
  Who did it, when and what she added stay on the note. A note cleared once cannot be cleared again.
- The coordinator can approve a **word** for a catalogue item ("ball pen" means Pen, `material_alias`): the model is shown it beside the item.
  A word cannot mean two items.
- She can approve a **unit** that converts ("dozen" is 12 piece, `material_unit_conversion`). Code converts only with such a row; the number
  must still be in the note's own words, so "2 dozen pens" becomes 24 piece, and "dozen pens" (no number) still waits. Without a row nothing converts.
- Routes (coordinator only, off while `educator.timetable_enabled` is off): `/materials/review/list|resolve|dismiss|alias|convert`.
  The page that uses them is 4b's.

## Verified
Run from `packages/engine` with the local database (`DATABASE_URL`, `TEST_DATABASE_URL`):
- `.venv/bin/python -m pytest tests/test_materials_review.py tests/test_materials_intake.py tests/api/test_materials_school_routes.py -q` → see the PR.
- Tests were written first and seen failing (import error, then three route tests failing, then the migration's missing `updated_at`
  column, which `apply_conventions` needs on any table that is updated; that gap is fixed in the migration).
- The migration was applied twice to a database that already had it (no error).

## Not done, on purpose
- No model call; the prompt is still inactive and the gold set is empty (rule 7).
- The review page (4b) and the photo upload route.
- Aliases are not matched by code: they only help the model. Code still decides what is confirmed.

## Handoff
- Push waits for the orchestrator's word that #393 is live and the migration slot is free; the orchestrator rehearses and merges the migration alone.
- Next: 4b's review page calls the five routes; Nimish approves bars, the cap and the inventory number.
