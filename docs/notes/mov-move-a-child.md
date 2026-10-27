# mov_move_a_child — a coordinator changes a child's grade or moves them to another class

Goal: `goals/mov_move_a_child.yaml`. Nimish, 27 Oct 2026. Not a numbered slice of BUILD-ORDER: the class list (`core/roster.py`) gains the one
way to change where a child is, from the child's own page. One additive migration; no workflow's files change.

## Verified

- `bin/engine done mov_move_a_child` — every one of his sentences PROVED, all four criteria PASSED (engine 26, browser 6, types and lint, `bin/check` 34).
  NOT DONE only for what is manual: the rehearsal, and the live site (the live database did not answer from here).
- The same browser spec passes with the website as the `app_web` role and the engine as `app_engine` (what CI does), so the grants hold.
- All 108 migrations apply from nothing on an empty database; `bin/engine load --check` — unchanged on a second run.
- Tables that carry a child's class or grade as copied text: 2, `sheet_instance.section` and `sheet_template.band` — both say where a paper was
  printed, and stay (`test_two_tables_carry_a_childs_class_or_grade_as_text_and_both_are_a_printed_paper` fails if a third appears).

## Handoff

- Live: nothing. Needs `rehearse-update-live.yml` run on this branch before merge. Migration `20261218090000` (main's newest was `...216090000`; open PR #337 takes `...217090000`).
- The owner opens the child on Children → "Grade and class". The roster file still lists where the child was: the loader leaves that row alone and says "left as changed here".
- Known, not fixed: a returned *library worksheet* is matched to a child by the name or roll written on it, within the class the file was uploaded for
  (`w3_read/copies.py`); a moved child's old worksheet scanned under their old class will not find them by name (an error is raised), and a roll number written on it finds whoever holds that roll in the old class now.
- Not done: bulk moves, undo (a move back is a move), names, deleting a child.
