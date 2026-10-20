# ADR 0085 — Grades are read from the table, every grade a row holds is a key, and "G2+" is Grade 2

**Status:** accepted (2026-10-20).
Goal: goals/b0b-grades-from-the-table.yaml

## What happened

B0a (ADR 0084) made the `grade` table; nothing read it. The website listed Grade 1 to 4 and "Reasoning · Grade 2 and
up" in its code, so a Grade 10 skill had no place on the curriculum page. Ten files read a grade's number out of its
code (`"G10"[1]` is 1, `left("G10", 2)` is "G1"), and seven queries sorted grades as text ("G10" before "G2"), the
database's own rule for a class's grade (`class_band`) among them (tests/test_grades.py listed each before the fix). Ten columns held a grade as text the database never checked,
and a level's grade sat in `skill_set.level_band`, a JSON object no key reaches.

## Decision

- **One read of the table.** The website reads the school's grades once a request (`grades()` in `lib/queries.ts`):
  each one's code, name and order. SQL orders and compares by `grade_ord(tenant, code)` or a join to `grade`. The
  engine does the same in SQL. Nothing parses a code.
- **Every grade a row holds is a key** on (school, code) into `grade`: `rung`, `child`, `sheet_template`, `blueprint`,
  `level_rule` and the registry's `milestone`, `learning_objective`, `activity`, `report_item`, `trait`.
- **A level's grade is checked as a key would be** (`level_band_is_keyed`): each level a row of `difficulty`, each
  grade a row of `grade`, refused with a key's own error; a grade a level names is not deleted or renamed from under
  it. A true key arrives with B1, when a level is a row (`skill_level.grade`).
- **"G2+" is Grade 2** (Nimish's decision, B3 on the design): it meant first met in Grade 2, which is what every
  level's grade means. A paper gives a child the levels of their grade and the grades below
  (goals/f1e-the-grade-plan.yaml), so a Grade 3 or 4 child is still given reasoning. The week's declaration offers a
  class the skills with a level in its own grade only (goals/n4-week-declaration.yaml, and "nothing else" for Grade 1),
  so a Grade 3 or 4 class's week no longer lists the two reasoning skills, which "G2+" had added to every grade from 2
  up. Open for Nimish: move a reasoning level to Grade 3 or 4 on its skill's page, or say the week should list them.
- **The maths library keeps its paper's layout for the youngest grade** (`render.py`: bigger boxes, two to a row,
  when `sheet.grade == "G1"`). It is how the library draws a paper, not a list of grades a page or another subject
  reads (decision B4 on the design); moving it to a column would change no paper and is left until a second layout
  exists. The test that no file names a grade exempts `engine/assess/` and the proofs (`engine/checks/`), whose
  requests are in the school's terms.

## What it changes for a person

- The curriculum page and every grade filter list the grades the table holds, in its order; a Grade 10 level shows
  under Grade 10, after Grade 9.
- Reasoning's two skills sit under Grade 2; the "Reasoning · Grade 2 and up" group is gone.
- The 144 reasoning library worksheets print "Grade 2" where they printed "Grade 2+"; the other 2,593 are the same to
  the byte (STATE.md "B0b").
- A level's grade can be set to any grade the table holds, Grade 10 included.
- A Grade 3 or 4 class's week declaration no longer offers the two reasoning skills (above).
- The menu says "Grade 1–Grade 4 · Maths", the lowest and highest grade a skill is in, where it said "Grade 1–4".

## Rejected

- **Keep "G2+" as a grade row** ("Grade 2 and up"). A grade a child cannot be in, kept only to sort reasoning into a
  group of its own; every other level already means "this grade and up".
- **Let the week's declaration list a class's grade and the grades below.** Tried: it broke the Grade 1 week Nimish
  asked for on 2026-10-06 (every skill Grade 1 teaches "and nothing else"; tests/test_week_note.py).
- **A key on `level_band` now** by splitting it into rows. That is B1's step (`skill_level`), with its own proof that
  every question drawn is the same; done here it would be B1 twice.
