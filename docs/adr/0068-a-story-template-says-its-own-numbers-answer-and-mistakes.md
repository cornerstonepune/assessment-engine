# ADR 0068 — A story template says its own numbers, its answer and its mistakes

**Status:** accepted (2026-10-11, slice M4d1 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md4d1-times-stories.yaml

## What happened

MD.WORD is the drafted document's stories with × and ÷, 26 cases at Grades 2 to 4. Measured before the build (STATE.md
"M4d — measured before the build"):
- **Ten drew nothing.** Times as many, the smaller (B09) and how many times (B10), and half as many (B27) had no
  template. The six two-step stories with × and ÷ (B18–B23) failed: their rule gives no size, and the two-step maker
  works its first step with + or − only (`evaluate` reads a signed sum). A number the story does not need (B25) and a
  price list (B26) had no × template.
- **A story's numbers came from the level, not the story.** "Half as many" is ÷ 2 whatever the level's sizes; a
  two-step story's four numbers have no single level size; the assumption A9 asks each template to say the range its
  numbers may take, and 2 of 76 did.
- **Drawn on MD.WORD's levels, the older stories drew past their grade** (found while looking at what the build
  drew): a level that gives no size let the drawer take 2 digits by 2 — "A shelf holds 75 books. How many books are
  there on 72 shelves?" at Grade 2, "₹9459 for 3 bus tickets", 4-digit remainders.

## Decision

1. **A template that carries `numbers` and `answer` is a story of its own kind** (`assess/own_stories.py`): `numbers`
   gives each number's range ([lo, hi], or one value: half as many is ÷ 2); `answer` is the formula the child works
   (`a*b+c`, `(a+b)/c`, `a/(b+1)`), worked exactly — a division that does not come out exact draws again, so no story
   asks for 2.5 pens; `also` names each mistake by the formula of the wrong answer it writes (`a*b`: one step only);
   `least` is the smallest answer that asks something (how many times is never 1); `differ` the numbers the story
   must tell apart ("2 pencils cost ₹50. What do 2 pencils cost?" is drawn again). Every question names a mistake or is
   drawn again.
2. **The older makers never draw one** (`words.owns`, `words.older`): the + and − makers, the × maker and the ÷ story
   maker draw from the templates sized by a level's rule, as before. A case whose shape has templates of the new kind
   draws them (`bands._story`, `divide_stories.story`); a case read from a table asks for a story with one (`context`).
3. **A price list is a template's table with its numbers named** (`["Pen (₹)", "b"]`): the story asks for one item, the
   list prints both, and reading the other row is a mistake of its own.
4. **MD.WORD's levels say their sizes as rows**: 1 or 2 digits by 1 at Grades 2 and 3 (`digits`), as MUL.2D1D's
   Grade 2 levels place 2 digits by 1. A table fact for every case was tried and rejected: the × stories carry no fact
   tag and dropped out of the level.
5. **The scenario check works a two-step story out a second time** (`checks/stories.py`), from its numbers and its
   shape, apart from the formula its template carries.

## Rejected

- **A two-step maker in code per shape**: six functions for six formulas, and the next shape another function; the
  formula is a row the school can read and change.
- **The case rows carrying the sizes** (as V01's do, M4b1): fifteen of MD.WORD's cases have another home whose level
  sizes them differently (B06 is 2 digits by 1 on MUL.2D1D); a case that fixed its size would contradict it
  (`taxonomy.within`).
- **`eval` of a template's formula**: a formula is data; it is parsed and worked by + − × ÷ and brackets alone.

## Consequences

- 22 new template rows; the 76 older ones keep their makers until M4d2 gives each its range (A9).
- Six mistakes drafted for Achal, five new codes and "times as many" read as "more" for a story that divides; each
  counts against NUM.PRB.02, as `M_TIMES_AS_MORE` does for ×.
