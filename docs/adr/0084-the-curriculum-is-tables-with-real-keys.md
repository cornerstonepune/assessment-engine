# ADR 0084 — The curriculum is tables with real keys, built in steps that change no paper

**Status:** accepted (2026-10-20).
Goal: goals/b0a-the-vocabulary-is-tables.yaml

## What happened

The audit of the backend (claude.ai/code/artifact/71c2aaf5-06c1-49b7-bcd5-2e6761154e9e, "Backend" tab, checked against
the schema, seed and code on 2026-10-17) found the content held but not the structure:

- a skill's levels, their grades and approvals live in JSON blobs on `skill_set` (178 levels in `difficulty`), read or
  written by 40 engine files and 14 website files;
- subject → topic → skill are tied by plain codes the database never checks;
- 66 places in code name structure that should be rows: a grade list that stops at Grade 4, "G10" cut to "G1" in four
  queries, the four level names copied 26 times, the six child states with their words and colours in code.

Nimish, 2026-10-20: "we need proper tables", and "everything is now getting built in a proper, scalable way, not as
some one-time random effort". All backend first: B0–B4 (BUILD-ORDER.md), before Hindi or any new screen.

## Decision

- **Vocabulary is tables.** `grade` (PG, N, K1, K2, G1–G10), `difficulty` (Easy, Medium, Hard, Advance) and
  `child_state` (the graph's six states), tenant-scoped like every table, each with its order, so sorting is by a
  number and never by text.
- **Every link is a real key.** Composite with `tenant_id`, so a school's rows point only at that school's vocabulary.
  A list of allowed words in a CHECK becomes a key into the table that holds them; adding a grade, level or state is
  an insert (CLAUDE.md rule 1).
- **What a person reads, edits or links to is a column or a table; what only a generator reads stays as data in one
  row** (a level's rule for drawing numbers, a question type's template), checked against the tables it names.
- **The target** is the Backend tab's section 5: three vocabulary tables, `subject` / `topic` / the skill with real
  keys, then `skill_level`, `question_type`, `skill_level_question_type`, `skill_level_sample`, `skill_mistake`,
  `skill_prerequisite`, `skill_registry_link`, and a history table beside each that changes.
- **In steps, each proved to change nothing** (section 7): a numbered migration rehearsed on a copy of live, a check
  comparing the new tables with the old answer, no paper or child's map changed on the day. B0a only adds the tables
  and keys; readers move in B0b–B0d.
- **The seed is the source of the rows**; the database makes the same rows for every school, those there when the
  migration runs and any added later (a trigger on `tenant`), because a key needs its rows before any load runs. A test
  adds a school and compares its rows with the seed, so the two cannot drift.
- **The rehearsal applies a new migration after live's rows arrive**, as `bin/update-live` does on live. Until now it
  applied it to the empty copy and then restored live's rows with their triggers (and so their keys) off, which could
  not show that live's rows satisfy a new key.
- **B0c: a level's worksheet letter is a column, set by the seed** (`difficulty.letter`: E, M, H, A, one level's alone),
  and the level a paper is at when nothing says otherwise is one config row, `level.usual`. The maths library
  (`assess/placing.py`) keeps naming levels in its own rule for which level a question's shape belongs to (a straight
  calculation at the hardest of the first three it fits, any other kind at the last): pure maths, outside the test.

## Rejected

- **1EdTech CASE as the internal schema.** CASE is an exchange format for publishing frameworks: items and associations
  as generic documents. Used inside, every skill, level and grade would be an untyped item and every link an
  association row the database cannot check by kind, which is the looseness this work removes. Every skill and level
  keeps a stable id, a code and a grade, enough to export to CASE when a partner needs it.
- **Keeping the JSON blobs, with checks in code.** The blob is why a level's grade is free text and its approval cannot
  be joined; a check in code holds only where that code runs, and the website writes these rows too. A key holds
  wherever the row is written.
- **Everything in one migration.** 54 files read the levels blob; moving them at once could not be proved
  reader by reader, and one mistake would change papers on the day.
- **A CHECK listing the words, as before.** Adding a grade or a state would be a migration; the words, colours and
  order would still live in code.
- **A level's letter as its initial, computed (B0c).** Easy, Medium, Hard and Advance each start with a different
  letter, but a school adding "Expert" could not: its codes would clash with Easy's. The letter is written down instead.
