# C1 — every question names its skills in the registry (goals/c1-questions-name-their-skills.yaml)

## Verified

- **Before the code (fresh build of main, 23,909 bank questions):** `tests/test_question_registry_skills.py` 6 of 7
  failed — no `item_registry_skill`, no `declared` on a level's kinds, `skill_set` still a view. (The seventh runs the
  migration itself.) Every question's counted skill (`spec ->> 'skill'`, else the first of `skill_codes`) was already a
  real registry key; 11,913 sit in skills whose registry list holds more than one skill.
- **Built:** migration 20261204090000 — `item_registry_skill`, one row per registry skill a question tests (a real
  key), a mixed question's rows each with its step's number and words; every question starts with the skill its results
  already count; a new question gets the same row by itself, and a re-imported legacy question's row follows its skill;
  at commit the database refuses a question with no skill, or with two and a row naming no step. Applied twice locally
  (1.3 s, then 0.2 s): 28,700 rows, one per question.
- **E0's fragility, at its cause:** a level's kind now says whether the curriculum declared it (`declared`); the bank's
  sync adds and removes only its own. The 395 links on a fresh build all came from the bank (`declared` false). A new
  question type no longer clears a declared kind; a kind the bank stops holding still goes (test).
- **B4b's `skill_set` view dropped**, as B4b's note said the next schema slice would; no file reads it.
- **`engine past --curriculum`:** the questions and the levels as counts and checksums; the rehearsal diffs them before
  and after the migrations (not after update-live, which writes the bank as it is meant to).
- **Tests:** `test_question_registry_skills.py` 7 passed; `bin/check` 30 passed.

## Handoff

- **Live:** nothing; waits on B4/B4b being migrated on live, then this PR's merge.
- **In flight:** whole engine suite, whole web suite, CI, the rehearsal on a copy of live.
- **Next:** C2 — one evidence record for every kind; the graph then reads a question's skills from these rows.
- **For E0 (PR #284):** its loader should write `declared = true` when a link already exists (`on conflict do update`);
  its test that the English links drop to 0 after a type write now sees them kept.
