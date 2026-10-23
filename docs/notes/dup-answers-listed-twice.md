# dup-answers-listed-twice (W3, gate R1b: the 21 Oct file read again, shown honestly)

Nimish, 2026-10-23: "why are there duplicate entries"; "if there are blank answers, why is the system considering this as right?"
Goal: `goals/dup_answers_listed_twice.yaml`. Read side only: no row changed or removed (rule 4); reader, prompts, marking untouched; no migration.

## Verified

Each claim, its command, its last output (local throwaway database built by `bin/testdb fresh`, never live).

| Claim | Command | Last output |
|---|---|---|
| The assessment lists each child once; a never-handed-back second copy beside a read one is said under the table, not counted | `bin/engine done dup_answers_listed_twice` (test 1) | PROVED, 1 passed |
| A child's page lists each answer once; the header count, each skill's "n of m right" and the graph's `child_skill_state` equal the answers recomputed from `evidence_event` | same (test 2) | PROVED, 1 passed |
| Two readings told apart: "What the reader saw" ("reader saw nothing" when blank) and "What the child wrote (you confirmed)" | same (test 3) | PROVED, 1 passed |
| All-blank and none-right copies say so beside the score | same (test 4) | PROVED, 1 passed |
| The papers, card, across-classes, child and report-card pages still hold | the goal's first criterion | 33 passed |
| On the old code the same four checks fail (child page: "Expected 3, Received 9" rows, three skills) | stash `apps/web/lib` + `apps/web/app`, run the spec | 4 failed |
| `bin/check`, `npx tsc --noEmit` | the goal's criteria | 30 passed; passed |

`engine done` ends NOT DONE only because live did not answer from here (I did not connect to it, by instruction).

## Causes

1. **Two copies a child.** `focus_paper.print_paper` (used by the maker for a class assessment) inserts a new sheet and a new code every time; only a *home* assessment is replaced by the newest made. A class assessment made twice gives every child a second sheet, and the list counted every sheet as a copy. Established from the code and reproduced on the copy; whether live holds two sheets per child is read from the page, not proven here. Not changed: stopping a second make is the maker's (W2), a decision for Nimish.
2. **Each answer listed twice.** A signed-off answer is one evidence row per skill its question tests (`evidence_placed`, already named in `answer_placed`'s migration). The child page listed rows, and gave each skill's line every row of its rung. Stored once; shown once per skill, each skill's line then every skill's rows.
3. **"— | 10 | right".** "Child wrote" was the reader's own reading; a person's check is a new `read_correction` row that never changes it (rule 4), beside a mark that is the person's. The dash was the reader's blank, the 10 the answer *key*.
4. **0 of 12.** A paper whose answers are all blank or all wrong scores 0 of N, and nothing said so. Now says "every answer blank" or "none right: is this the right page?".

Counts: the child header counts `answer_placed` (once an answer); `child_skill_state` counts an answer once on each skill it tests, by design. No stored or graph number was doubled. The assessment's score sums the copies read: it would count a child twice only if both of their sheets were read — not seen here.

## Handoff

- Open: should the maker refuse a second class assessment for the same class, week and skill (W2)? Not done.
- Open: the upload list shows the same file three times (issue 3 of the report); not touched.
- Open: evidence on a skill the skill set's registry list does not name has no line on the child page (seen while testing); not touched.
- Live check after merge: the 21 Oct Grade 1 assessment, and a child's page.
