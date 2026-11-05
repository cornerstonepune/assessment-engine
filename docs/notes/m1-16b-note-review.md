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

## Review (/code-review medium) and what was done
Fixed at the cause: a conversion applies only if the unit is written in the note's own words (a unit the model only claimed does
not multiply a number); the converted quantity is exact decimal arithmetic (0.7 dozen is 8.4, not 8.399999999999999); clearing and
setting aside check the school inside the module, not only in the route (one lookup, 404 for no such note, 409 for already cleared);
an alias is one insert that yields to the unique row; a changed conversion factor is a **new row** (the table is append-only, the
latest is used) so who approved what, and when, is kept.
Prompt: v1 told the model to give "the catalogue's unit", so no approved conversion could ever fire, and it never mentioned aliases.
`materials_read` **v2** (inactive, like v1) shows aliases and asks for the unit as the note wrote it. It makes no call and has no score:
it becomes active only after `engine eval materials_read` meets the bars on a gold set (rule 7); until then conversions and aliases
are code that waits for a prompt that can use them. Not accepted: "any staff can use the review routes" (the routes require the
coordinator role; the test `test_the_review_routes_are_for_the_coordinator_only` shows an educator gets 403).

## /simplify (4 angles) and what was done
Applied: one `materials_text.norm` for every stored and looked-up word and unit (they must match character for character); an
index on `material_alias (tenant_id, material_code)` (the catalogue read looks up by it); "boxes" and "dozens" match their unit;
a factor is compared as a decimal, not a float; a line a person adds from a waiting note is marked `via: note_review`, apart from
`note` (code confirmed it), so the trail tells them apart; dead and duplicated test lines removed.
Skipped, with reasons: one shared error-to-status handler for the routes (the messages differ per route and a handler would
touch routes outside this brick); factors as `Decimal` end to end (changes `materials_list.add`'s signature, outside this brick);
`approve_alias` as one `do update` statement (the table's `updated_at` trigger has no column to touch there); a view for the latest
factor (two short reads, one definition each use; both order by approved_at desc, id); a page size on the review list (a
backlog of waiting notes is small and the page is 4b's); lazy load of conversions (one small query per note, before the model call).

## Not done, on purpose
- No model call; the prompt is still inactive and the gold set is empty (rule 7).
- The review page (4b) and the photo upload route.
- Aliases are not matched by code: they only help the model. Code still decides what is confirmed.

## Handoff
- Push waits for the orchestrator's word that #393 is live and the migration slot is free; the orchestrator rehearses and merges the migration alone.
- Next: 4b's review page calls the five routes; Nimish approves bars, the cap and the inventory number.
