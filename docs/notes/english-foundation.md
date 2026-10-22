# English foundation, Grades 3 and 4 (goals/english-foundation.yaml)

Content only, as drafts: BUILD-ORDER keeps the build on maths (W1, gate 3), so no migration, engine code, endpoint or
screen for English. The rows are in `docs/drafts/english/`, shaped like the maths seed tables (`skill` as
`skill_set`, `skill_level` as B1's table, `skill_level_sample`, `skill_mistake`, `skill_prerequisite` as B3's,
`question_type` and `skill_level_question_type` as B2's), so they load as rows when BUILD-ORDER reaches English.
Grade 3 = Cambridge Primary English 0058 Stage 3, Grade 4 = Stage 4 (Nimish, 2026-10-21).

## Verified

- **The framework is the recorded copy.** `research/english_check.py` reads it through
  `research/crosswalk_cambridge.py`, which refuses a file whose sha256 is not
  `dd7f86fe98586fd7676939b67b59b82e989f1124dd40603ec44fbb552804082c` (docs/crosswalk/sources.json). Fetched
  2026-10-21: the hash matched; 581 objectives read word for word, 102 at Stage 3 and 106 at Stage 4, every
  fingerprint equal to `docs/crosswalk/statements/cam-pri-eng-0058.json`. Cambridge's words are not committed.
- **Counts** — `python3 research/english_check.py` (last line `0 faults`):

  | | Grade 3 | Grade 4 |
  |---|---|---|
  | Cambridge objectives | 102 | 106 |
  | on a printed paper, through skills | 73 | 79 |
  | observed by an educator (not on paper), with reason and how | 29 | 27 |
  | skills | 52 | 57 |
  | levels (Easy, Medium, Hard, Advance) | 208 | 228 |
  | worked examples with answers | 624 | 684 |
  | of which marked by code / by a model with a rubric | 490 / 134 | 518 / 166 |
  | passages | 73 | 93 |

  Both grades: 340 named mistakes (`M_ENG_…`), 390 skill–mistake links, 7 rubrics on the drafting method's scale
  (Beginning, Developing, Secure, Extending), 18 question types (12 marked by code, 3 by a model with a rubric, 3
  by the educator and never on a paper).
- **What code checks, on every row:** every objective code is in the framework and of the skill's stage; every Stage 3
  and 4 code is on a paper or observed, never both, none dropped; each skill's sentence passes the drafting method's
  words (`research/crosswalk_drafts.py`); no two skills of a grade alike (name or sentence ratio above 0.85); every
  "before" is a real skill taught earlier; the teaching order follows the school's numbered units
  (docs/spine/sources/school_units.json); every skill has the four levels, each a one-line rule with at least one
  key code checks, and exactly three examples; each example's shape for its type, its level's rule (passage, text
  and answer lengths, options, spelling pattern, mistakes to correct, answer in the passage), and 186 answers
  worked out again from their rule (verb endings, plurals, possessives, affixes, compounds, contractions,
  alphabetical order, the order of events in the passage, index pages, similes, alliteration, the narrator);
  every wrong answer named a mistake of its skill; every mistake used; British spelling; no run of six words shared
  with the framework's text, and none of Cambridge's own "e.g." words as an answer or option; the derived rows
  (`topic`, `objective_coverage`, `skill_objective`, `skill_prerequisite`, `skill_level_question_type`) current.
- **Tests** — `cd packages/engine && .venv/bin/python -m pytest -q tests/test_english_foundation.py`: 14 passed,
  including that a dropped objective, an invented code, a wrong key, a missing example, a before that points
  nowhere, a twin skill, Cambridge's sentence and Cambridge's own example word are each caught.
- `bin/check`: 28 passed, lint clean.

## Handoff

- **Live:** nothing; drafts only.
- **In flight:** the school's English educator reviews the document (link in the PR) skill by skill: approve, edit or
  comment. Edits come back into `docs/drafts/english/` and `python3 research/english_check.py` re-checks them.
- **For the educator, flagged by the drafting:** answers code cannot work out (stress, sound groups, fact or opinion,
  theme, order of strength) are as drafted; table boxes and gap answers may need wider accepted answers; a few
  real places and facts in passages to confirm; library labels in EN4.TEXT.FICTION are invented and should match the
  school's; the school lists no Unit 5 for Grades 3 and 4.
- **Next:** when BUILD-ORDER reaches English, a subject row `ENG` and a loader for these files, after B4's rename.
- **Blocked:** nothing.
