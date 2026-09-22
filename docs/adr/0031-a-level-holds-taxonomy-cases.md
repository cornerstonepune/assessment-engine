# 0031 — A level holds named taxonomy cases; a case is a combination of measured tags

Date: 2026-09-22
Status: accepted (step 8e–8i, `BUILD-ORDER.md`)

## Context

The school team's *Addition & Subtraction Assessment Skill Taxonomy* treats a question as its own case
whenever a child can make a different kind of mistake on it — in columns or in a line, the shorter number
first, a carry from the ones or from the tens, a zero, an answer that loses a digit, the box first or
second, a missing digit, a story's shape, a planted mistake. Measured on the live bank on 2026-09-22 (269
cases after the document's sections were read case by case): 102 held a worksheet's 12 questions, 11 fewer,
156 none. Some gaps were a level's rule naming a key no generator read — `order: shorter_first`,
`layout: horizontal`, four budget levels asking for different costs and printing the same problem.

## Decision

- **A case is a row** (`taxonomy_case`): a combination of tags (`match`), the document's own example as a
  question the tag code measures, and `min_items` (12, a worksheet). The document's §12 advice, taken as
  written: store dimensions as tags, select by combinations.
- **Tags are measured, never typed** (`assess/tags.py`): the finer dimensions the cases read — which columns
  regroup, zeros an exchange passes through, zeros in the answer, a zero operand, the missing number's and
  digit's place, a story's shape (read back from the template that wrote it) — are computed from the question.
- **A level lists the cases it holds** (`check.cases`), with bounds (`digits`, `max_total`, `layout`, …).
  The fill draws the same number of questions from each case and keeps a question only when, measured, it
  is that case (`assess/draw.py`); a level is the union of its cases (`verify.dimension_problems`).
- **A rule key no generator reads is refused** (`engine audit`, `bands.READS`). A level declares only what
  its questions will be.
- **Plain sums print half in columns, half in a line** wherever a case does not fix the layout.
- **The 2- and 3-digit skills keep their missing-number and story questions**, each a case of its own
  inside the level's number bounds, beside the plain sums — the worksheets the school already knows.
- **`engine bank taxonomy` is the check**: every case holds `min_items` questions in the active bank.

## Rejected

- **One skill per case (269 skills).** The document itself warns against encoding every combination as a
  topic; a child's skill is the outcome ("adds 3-digit numbers in columns…"), the cases are what a level
  of it must hold.
- **Leaving the levels and adding questions until the count is green.** A level whose rule does not say
  which cases it holds cannot be checked; the next fill would drift back.
- **A model writing the cases' questions.** Every case is a pattern of numbers or a story shape; code
  enumerates them for no tokens (ADR 0010), and the model is not asked to count carries.
- **The story templates as a table, or in `supabase/seed/`.** They are a data file inside the engine,
  `engine/assess/word_templates.json`: the generators in `assess/` are pure and read them without a
  connection, which a table would take from every story generator; and the server's image holds `engine/`
  alone, so a file under `supabase/seed/` stopped the engine starting on 2026-09-22 (`tests/test_image.py`).
- **Storing a question twice so two skills' levels can both hold it** (Grade 1's 12 + 5 and Grade 2's). One row
  per question is what keeps its worksheets, flags and evidence one history. Levels of different skills that
  share a case split its numbers, so a Grade 1 floor is measured after the refill: `ADD.1D.BRIDGE10` Medium has
  144 questions, 6 already Grade 2's and 7 retired rows, so 131 (ADR 0011).
- **Retiring the old questions wholesale.** Only a question its level's new rule does not hold is retired
  (through the flag path, which keeps it and says why); everything that still fits stays, with its worksheets.
