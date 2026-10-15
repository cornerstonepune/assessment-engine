# ADR 0075 — A kind of question is a row, approved once; a skill is made from its examples

**Status:** accepted (2026-10-15, BUILD-ORDER "Inserted now: a skill from its examples").
Supersedes F1g of BUILD-ORDER "One flow for the educator" (a level's questions approved before it goes on a paper), and
makes F1d's level approvals a record that gates nothing once SF2 ships.
Goal: goals/sf1-a-kind-of-question-is-a-row.yaml

## What happened

`engine week unapproved` on live (2026-10-15) listed 38 levels in 10 skills waiting for approval. Nimish, the same
morning, on approving questions level by level: approval belongs to "all unique formats of questions", with an engine
that "simply checks whether a certain question belongs to a certain format"; educators add or configure a skill by
giving examples of a format, as text, a PDF or an image, and the system makes the questions; "it should be skills *
format and 100/200/500 is for a skill and difficulty level combo"; each skill-level keeps its grade, as today. Achal's
Grade 2 multiplication asks are the first examples.

Measured the same day, on a copy of the bank (28,031 active questions, 43 skills):

- **A kind of question is Python.** Every kind is a function in `bands.NATIVE_GENERATORS`; the bank holds 313 skill ×
  kind pairs (`item.template`) and 570 skill × level × kind. One kind is made from data alone: the own stories
  (`own_stories.py`, `word_templates.json`), whose rows give each number's range, the answer as a formula of the
  numbers, and each mistake as the formula of the wrong answer it writes.
- **Achal's five asks against the bank:**
  - multiplying with zeros (10 × 200, 60 × 40, 700 × 50) exists, in MUL.TENS Hard and Advance (Grade 4);
  - multiples has "the multiples of 6 up to 44" and "is 18 a multiple of 8?" (Grade 3), but not "the 9th multiple of 3";
  - stories with × and ÷ (MD.WORD) mix the two at every level;
  - nothing makes a sequence or three numbers multiplied.
- **"100/200/500" is more than some levels hold.** Three numbers of 2 to 5 with a product up to 30 make 26 different
  questions. The 11th to 13th multiples of the 2 to 10 tables make 27. The first five multiples of those tables make 9.

## Decision

1. **A kind of question is a row** (`question_format`). It holds:
   - its words, with each number named in braces (`{a} × {b} × {c} = □`);
   - the answer, as a formula of those numbers, or a list of them;
   - each mistake, as the formula of the wrong answer it writes;
   - the educator's examples, kept as given.

   It uses the own stories' vocabulary (`numbers`, `answer`, `also`) and their formula worker (`own_stories.value`). No
   Python is written per kind.
2. **A skill's level holds the numbers.** Each level's rule gives the range of each number (`numbers`) and the bounds
   of the answer (`answer_within`), and names the kinds it uses (`cards`). Two kinds of one skill at one level share
   that level's difficulty. The grade stays per skill × level (`skill_set.level_band`): a grade uses its own levels
   and those of the grades below.
3. **Code decides whether a question belongs to a kind at a level.** The question's words are read back through the
   kind's template, which gives its numbers. The question belongs when:
   - every number is within the level's range;
   - the answer is within the level's bounds;
   - its stored answer and its named wrong answers equal what the formulas work out.

   The same check runs on a question just drawn, on one stored in the bank, and on an educator's example. A number is
   never a model's last word.
4. **Each level says how many different questions it can make,** counted, not guessed. The target is the skill ×
   level's own (`min_items`: 100, 200 or 500). A level that can make fewer is filled to all it can make and says so. A
   question is never repeated to reach a number.
5. **Approval is per skill × kind** (SF2), given on samples drawn from each level that uses it. A changed kind, or a
   changed level rule, withdraws its approval. Papers draw only approved kinds. The 313 pairs in the bank today start
   approved, because their skills were approved as wholes before. F1d's level approvals stay recorded and gate
   nothing.
6. **A kind is drafted from examples** (SF3). A model reads the educator's examples (typed, a PDF or a photo) and drafts
   the kind and each level's numbers. Code then checks that every example belongs, and the educator approves on
   samples. The draft is a prompt row with its eval, and Achal's asks are the eval's first gold.

## Rejected

- **Approving questions, level by level (F1d, F1g).** A level of 100 questions is approved by reading them. A corrected
  generator would ask for all of them again.
- **A model writing each question.** Its numbers would be its last word. Duplicates and drift could not be checked
  except by reading.
- **One Python generator per new kind,** as today. Every new kind would wait for a developer, and an educator could
  never add a skill.
- **The ranges in the kind rather than the level.** A level's difficulty would then live in as many places as it has
  kinds, and could disagree with the level's own words.

## Taken for Achal to confirm (WhatsApp, 2026-10-15)

Recorded in STATE.md as they are answered.

- Everything is Grade 2.
- Sequences Hard reads "90, 81, 72, 63" for his "100, 81, 72, 63". The checker refuses the latter: its steps are not
  equal.
- Three numbers multiplied:
  - Easy, each 2 to 5, product up to 30;
  - Medium, product 31 to 100;
  - Hard, 101 to 250;
  - Advance, 251 to 729 (9 × 9 × 9), with stories as a second kind.
- Multiples:
  - Easy, the 2nd to 10th multiples of 2, 5 and 10, and their first five multiples;
  - Medium, the same for 3, 4, 6, 7, 8 and 9;
  - Hard, the 11th to 13th multiples of 2 to 10.

  The WhatsApp said Medium covers "any table to 10". Medium leaves out 2, 5 and 10 so that no question sits at two
  levels: a question in the bank has one level, and the check refuses a level that shares one with another.
- Still open:
  - Advance for sequences and for multiples;
  - which Grade 2 level takes MUL.TENS's zeros (a level moved to Grade 2, no new kind);
  - whether × and ÷ stories become two kinds.
