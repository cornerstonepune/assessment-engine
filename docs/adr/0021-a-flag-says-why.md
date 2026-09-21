# 0021 — An answer that reaches a person says why it did

Date: 2026-09-21
Status: accepted

## Context

Nimish: *"242 is a lot of teacher approvals — you sure this is the best you can do?"*

The previous session answered by counting the flags into five classes, and the count was made by a
SQL query that *inferred* the cause from the shape of the stored reading: confidence is zero and
the state is `illegible`, therefore the region count must not have lined up. That inference put
five different failures into one bucket of 86 and made it the biggest class, which is what
`HANDOFF.md` then told the next session to work first.

It was the biggest class because it was the vaguest, and the story inside it was the wrong way
round. `HANDOFF.md`: *"the child works the whole method inside the box, so the region holds five
numbers where the paper asks for two."* Counted properly, **57 of the 74 hold FEWER numbers than
the question has answers, not more** — the engine is not drowning in candidates, it is not seeing
the child's answers at all. A nine-part question where one number was found flags all nine.

## Decision

**Every reading the engine does not stand behind records why, in the reader's own words**, as a
`why` on the reading beside `answer_state`. `2 numbers in the region for 3 answers`. `under the
confidence floor`. `ink in the box but no number`. `the printed question was not found on the
page`. `the answer to this question is not a number`.

A reading the engine *does* stand behind carries an empty reason, and so does a blank — a blank is
a claim about the child, not a doubt about the reading (rule 5), and giving it an excuse would blur
exactly the line that rule draws.

`bin/engine read waiting` is the count, replacing the query in `STATE.md`.

## Consequences

- **The teacher is told.** The approval screen already showed the crop and a plain sentence; it now
  says which of the five things went wrong, so she knows whether this is her judgement to make or
  the engine admitting it could not see. An answer under the floor she confirms in a glance; a
  region holding four numbers for two answers she has to split herself.
- **The next session works a fact, not an inference.** The classes are what the code did, recorded
  at the moment it did it.
- Readings taken before this exists have no reason and are counted as such rather than guessed at.
