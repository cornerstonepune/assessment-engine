# ADR 0044 — A mark follows the rule as it now stands: a reading is marked by what it says, and every deploy marks again

**Status:** accepted (built on Nimish's words of 2026-09-30: "odd + odd = odd. The child has written false, which is the
right answer … this would have happened with all the children. How do we do this?")
Goal: goals/s25-a-reading-is-marked-by-what-it-says.yaml

## What happened

Question 11 of the Grade 4 September Week 1 paper asks a child to tick True or Not true for four claims. The reader
leaves every tick to a person, and people type what the child ticked. Nimish typed "false" for "odd + odd = odd", and
the answer was marked wrong. The key was right ("Not true"), but marking compared "false" with "Not true" letter by
letter (`marking._against_the_key`). Eleven boxes on three papers ask this way: G3-SEPW1-A 11a–d, G3-SEPW1-B 9a–c and
G4-SEPW1 11a–d. Any child whose tick was typed "false", "no" or "x" was marked wrong, and papers were signed off that
way.

A marking rule put right did not reach answers already marked. `engine legacy remark` marks again only what the
reader read, on answers not yet signed off. An answer a person read stays as first marked. So did a signed-off one:
it changes only when a person saves it again (#131, ADR 0043).

## Decision

1. **A claim is marked by whether it says true** (`marking.TRUTH`). "true", "t", "yes", "y", a tick and "tick" are
   the key's True. "not true", "false", "f", "no", "n", "untrue", a cross, "x" and "cross" are its Not true. This
   holds on the papers' "True" / "Not true" and on the bank's "true" / "false" alike. Any other key is marked as it
   was before this ADR: by its letters, a number by its value, and a sign by the sign.
2. **Every deploy marks each answer a person read again by the rule as it now stands** (`marking.mark_again`,
   `engine legacy mark-again`, after the papers are entered). This runs as `correct` marks a save: an answer of an
   equation with its equation, a wrong answer with the mistake a person named on it.
   - A changed mark not yet signed off changes in place.
   - A signed-off one gets a new batch of evidence in the deploy's name (`correct_signed_off`), and the graph reads
     it instead; the old batch stays.
   - What the person read never changes.
   - An answer whose latest word from a person is a judgement (`read_correction.judged`) keeps it.
   - The deploy's log names every answer whose mark changed. `bin/update-live` and the rehearsal on a copy of live
     run the same step.
3. This amends ADR 0043's third decision. A signed-off box of an equation still changes at once only by its own save.
   Now the next deploy also brings it in line with its equation.

## Rejected

- **Changing the key to "false".** Every child whose tick a person typed "Not true" would then be marked wrong.
- **Asking people to save every affected answer again.** Nobody can tell which answers, among hundreds, a rule got
  wrong. Question 5 left this to a person on 2026-09-29, and those boxes waited.
- **A one-off command run by hand.** The next rule put right would need someone to remember it again. The papers are
  entered on every deploy for the same reason (ADR 0043).
- **Writing a mark whose status is unchanged.** Only a changed status (right, wrong, blank) is written. Otherwise
  mistakes learned or named since a paper was signed off would rewrite signed-off evidence that no rule corrected.
