# ADR 0054 — A model of multiplication is a kind or a shape of its own

**Status:** accepted (2026-10-10, slice M2d1 of BUILD-ORDER "Inserted now: multiplication and division").
Goal: goals/md2d1-multiplication-models.yaml

## What happened

`MUL.MODELS` lists eight cases of the drafted taxonomy: skip counting (G03), equal jumps on a number line (G04), an
array (G05), a table swapped to a known one (G14), a cell of the multiplication square (TF17), and stories of an array,
twice as many and area (B04, B11, B13). Measured before the build (STATE.md "M2d1 — measured before the build"), none
drew: three asked a kind for something it never made, one read a rule key its level did not set, the stories had no
template of their shape.

Two of the eight were filed by the draft as `bare_sum` — skip counting and a cell of the square — against the draft's
own rule, that "the methods, stories, missing numbers and the rest are other kinds, each naming what it is"
(`research/md_rows.py`). A `bare_sum` is "a op b =" to every reader of it: the website shows "5 × 5 = ___" for
5, 10, 15, 20, □; `verify` checks it as a straight sum; the page gives it a straight sum's working space.

## Decision

1. **Skip counting and a cell of the multiplication square are kinds** (`skip_counting`, `multiplication_square`):
   each a generator (`assess/times_models.py`), a picture (`pictures.DRAW`), a drawing on the website, a row of
   working space. The two case rows are corrected where they were drafted and written again by
   `research/md_taxonomy.py`. The square's context (a table) is its kind's, as a story's is a word problem.
2. **An array is a shape of equal groups** (`ARRAY`), measured as the array method as a picture of rings is measured
   as groups (`md_tags.SHAPES`, the one table); a case asks for it by its method, and the kind reads the shape back
   from that table. It is read in three labelled boxes, rows × in each row = in all, each box marked against its own
   key. The draft printed □ × □ = □ and counted 5 × 3 right for 3 rows of 5; the labels make one order the question,
   so no answer is marked by an order the child was not asked for. Achal may say otherwise; the boxes are a row of
   the picture, not of the marking.
3. **The number line is one kind drawn two ways** (`assess/number_line.py`): + and − as two jumps from a number, as
   before (moved whole out of `items.py`, its questions' keys unchanged); × as equal jumps from 0.
4. **The swap is an equation shape** (`SWAP_TO_A_KNOWN_TABLE`) reading the tables its level counts as known
   (`known`, a row: 2, 5 and 10 at Grade 2). A level that names none cannot make it, and says so. A level's rule
   reaches every equation through `equality.from_rule`; `equation`, frozen at 51 statements, is not touched.
5. **"Times as many" read as "more" is its own mistake** (`M_TIMES_AS_MORE`), named by the template row that says it
   (`added`), on both ways into the bank (`words.added_as`: the sampler, and a sentence checked by
   `verify.to_item`). Twice as many fixes its own 2 (`numbers`). A story whose misreading lands on the answer —
   twice as many as 2 is 4, and so is two more — is drawn again: it could not show the mistake it names.
6. **`MUL.MODELS` carries no `within`.** `placing.py` reads a skill whose levels say `within` as a calculation skill;
   `{"operation": "MUL"}` would hold 7 × 8 together with `MUL.FACTS`, two skills for one question. Its numbers are
   its kinds' own rule keys: `groups`, `size`, `known`, `digits`.
7. **`draw.py`, at its ceiling, gives what a case allows to `draw_case.py`** — the kinds it names, the operation an
   attempt draws, the digits of its numbers — and tells a kind the case's method, as it tells its shape.

## Rejected

- **Skip counting and the square as `bare_sum` printed by their method.** Every reader of `bare_sum` (the website,
  `verify`, the page's layout) would carry the same exception, and the next model would add another.
- **The square's context as a `table` in its spec.** A story's `table` is the rows the website prints; one key with
  two meanings breaks the reader that meets the other.
- **The swap as one more branch of `equation`.** The function is frozen at 51 statements and may only shrink.
- **Accepting both orders in □ × □ = □.** It needs a marking rule that reads three boxes together for one question
  kind; the labels ask the question that rule would have to guess.

## Consequences

- `MUL.2D1D`'s Advance holds "times as many" stories (B08), so its list names `M_TIMES_AS_MORE`: the seed for a new
  database, migration `20261031090000` for one loaded before.
- `items.py` is 101 lines shorter and its untyped findings 80 fewer; the number line is typed.
- Found, not changed here: the marker charges a wrong answer to every mistake that predicts it (3 × 3 answered 6 is
  "one row out" and "the numbers added"), while the counting kinds name neither for certain (`counting.named`).
  Named in STATE.md; the rule belongs to `marking.py` and `misconceptions.predict`, which this slice does not touch.
