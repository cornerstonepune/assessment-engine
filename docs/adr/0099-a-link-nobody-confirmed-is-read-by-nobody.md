# 0099 — A link between skills is proposed until a member of staff confirms it, and nothing reads a proposed one

Goal: goals/m1-15-skill-links.yaml

Nimish, approved 2026-11-04 (M1-15, as the orchestrator relayed it). The skill graph had one table of what comes before
a skill, `skill_prerequisite`, between the maths micro-steps (`skill`). It could not connect K2's skills, which are
broad skills (`registry_skill`): only 13 of 244 broad skills have a link to a micro-step, and none of K2's 169 distinct
activity skills is a micro-step. It also kept no reason and no one's word: 282 rows, drafted by a grade rule ("a skill
after every skill of its topic on the nearest grade below") and with the English foundation, not one checked by a person.

## Decided

- **A second table, `skill_link`, between broad skills**, with strength (`hard` or `soft`), a one-line reason, the source,
  a status (`proposed` or `confirmed`), and who confirmed it and when. Strength and status are rows (`link_strength`,
  `link_status`), as the repo keeps its other words; `link_status.confirmed` says which states a reader may use, so no
  view and no trigger names a state.
- **`skill_prerequisite` gains the same words.** Its 282 rows are `proposed`, source `seed rule`, strength `soft`
  (a grade rule cannot say a step is needed), each with the reason it was drafted. None is confirmed.
- **Readers see confirmed links only**, through `skill_link_confirmed` and `skill_prerequisite_confirmed`. A test fails
  if any engine or website source other than the seeders names a raw table; two further views
  (`skill_link_audit`, `skill_prerequisite_audit`) show every row for the checks that count them, and a second test names
  the only files that may read them.
- **A ring is refused** when it is proposed, not found when it is confirmed: the trigger of `skill_prerequisite` repeated
  for `skill_link`, counting every status.
- **Loading and confirming are fixed commands** (`engine skill-links load`, `engine skill-links confirm`), each one
  database function, so the engine holds no SQL of its own about these tables. The first confirmation stands; a second
  person's does not replace it.
- **The seeders make proposals.** Neither seed was checked link by link, so each row they insert is `proposed`, with
  source `seed rule`.

## Rejected

- **Marking the 282 confirmed**, so nothing changes for anyone. Nobody has checked them; confirming them would be the
  school's word given by a script. Nothing reads them today, so marking them proposed costs nothing.
- **One table for both spaces.** The two spaces have different keys (`skill` and `registry_skill`) and a link between
  them does not exist for K2; a single table cannot hold a foreign key to either.
- **A column of status values in a CHECK**, as `skill_prerequisite_not_itself` does for its rule. The repo keeps
  vocabularies as rows (ADR 0084); a new word is an insert.
- **Soft-delete.** DELETE is revoked on the new tables; a wrong link is withdrawn by a new decision, not removed. The
  withdrawal itself (a way to un-confirm) is not built here.

## Not built here

Any model proposing links, `relates_to` and `part_of` links, soft-edge suggestions on screens, and any screen. No
paper, child state or K2 observation reads a link yet.
