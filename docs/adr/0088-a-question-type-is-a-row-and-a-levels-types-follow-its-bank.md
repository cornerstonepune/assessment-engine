# ADR 0088 — A question type is a row, and a level's types follow its bank

**Status:** accepted (2026-10-21), from the decisions Nimish chose (docs/drafts/b2-b4-decisions.md). Builds on ADR 0077 and 0087.
Goal: goals/b2-question-types-are-rows.yaml

## What was found

Measured on the seed and on a copy of live (rehearsal 39560151627; `docs/notes/b2-question-types-are-rows.md`):

- 74 types (ADR 0077's formats) in 394 level × type links, on live and on the seed alike.
- The skills' `formats` lists are not the list of a level's types. They name 32 printed formats, not 74 types; in 11 of 46
  skills they differ from what the bank holds (multiplication and division take their kinds from their cases, not the
  list). And they are two things at once: the formats the generator makes a level's plain sums in where the level names
  none of its own (146 of 178 levels), and the order kinds print in on a library worksheet.

## Decision

1. **A type is a row** (`question_type`): its words (the 33 labels), how it reaches the child (`drawn` where the maths
   library draws its format, else `printed`), how its questions are marked (a list: four types mix computed and judged
   questions), and whether it prints its own words. **One rule** (`question_type_of`) puts a question in a type: its
   template's row, else its printed format's. A template that is only a level's numbers has no row, so no regular
   expression is needed after the migration's first fill.
2. **A level's types are rows kept equal to its bank** (`skill_level_question_type`), by a trigger on the bank's own
   writes, as ADR 0087 keeps a level's row equal to its blob. "Every level uses exactly the types it used before" holds
   by construction, and a test checks it against ADR 0077's rule worked out independently.
3. **The skills' `formats` list stays only as the generator's input.** Every reader that asked it which kinds a level
   holds (the library's print order, the eval's choice of a skill with stories, the website) reads the links. The
   generator, its prompts and cases, and the check that each listed format can be made still read the list.
4. **One approval per type** (`question_type_approval`), given with `engine types approve`, never edited.
5. **One gate** (`drawable_item`): active, at a confirmed level, of an approved type. Every path that puts a question on
   a paper reads it, and a paper that cannot be made names the level or type that waits.
6. **The day it ships, nothing is refused:** every type on a paper, or at levels all confirmed, starts approved
   (`internal.question_types_start_approved`, run once by the migration). A type a later seed adds waits.

## Rejected

- **Links as the generator's declaration** (the generator makes only a level's linked types). The generator chooses a
  question's template from the level's rule and cases in the maths library; making it read links rewrites the library
  (rule 10), and every paper would have to be proved the same through a new generator. Not this step.
- **Moving the `formats` list into each level's rule now.** It would change the rule of 146 levels on live, filing a
  version of each for no change a person sees. Left for Nimish to decide with B3/B4 (the note's handoff names it).
- **Links seeded per level in `skill_sets.json`.** A second list to keep equal to the bank by hand, where the bank
  already says which types a level holds.
- **Approval rows that can be withdrawn here.** Withdrawal is SF2a's (a changed kind withdraws its type); B2 only gives.
