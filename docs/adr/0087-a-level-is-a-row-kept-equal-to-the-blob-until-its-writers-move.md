# ADR 0087 — A level is a row, kept equal to the blob until its writers move

**Status:** proposed (2026-10-21), waiting on Nimish's approval of the goal.
Goal: goals/b1-levels-are-rows.yaml

## What happened

B1 (BUILD-ORDER.md, ADR 0084) moves each of a skill's levels out of three JSON objects on `skill_set` —
`difficulty` (words and rule), `level_band` (grade) and `level_approved` (approval) — into `skill_level`, one row per
skill and level (178 in the seed), with keys into `skill_set`, `difficulty` and `grade`. About fifty files read the
blob, and the website and the loader write it. B0c and B0d (PRs #228, #231) are still open and change many of the same
readers.

## Decision

- **The blob stays the one place a level is written, for now; a trigger keeps the rows equal to it.** Any write to
  `skill_set` (the website's edit, approval and grade move, the loader, `engine ratify`) or to a rung's grade remakes
  that skill's rows, as their owner. Nobody else may write `skill_level`. So a reader that has moved and one that has
  not can never disagree, and no paper, map or page changes on the day.
- **Readers move one by one**, each proved by `engine levels check`: level by level the rows give back the blob's words,
  rule, grade and approval; the counts per grade and of approved levels are equal; and the generator's questions drawn
  on one seed from the row's rule are the blob's. The rehearsal runs it on a copy of live before and after update-live.
- **A reader that wants every level's whole rule** (the generator, the mistake list, the cases a level names) reads
  `public.skill_levels(tenant, skill)`, which builds the blob's object from the rows, so it is handed exactly what it
  was. A reader that wants a level's grade or approval joins `skill_level`.
- **History is the level's own.** `skill_level_version` files a level's previous words and rule when they change, and
  only that level's; the migration carries each level's history out of `skill_set_version` once.
- **A level's words are kept whole in `looks_like`.** How they split into a learning objective, what it looks like and
  samples is Nimish's and Achal's call (B3); `learning_objective` waits empty until then. Nothing is guessed.

## Rejected

- **Moving the writers in the same step** (the website and loader writing rows, the blob derived from them). The
  website's writers sit in files B0c is rewriting, and the approval logic lives in `skill_set_version_on_change`;
  moving both at once could not be proved reader by reader, which is the reason ADR 0084 gives for steps.
- **Writing both from the application** (the site and the engine each updating blob and rows). Every writer would have
  to remember; one that forgot would make the two disagree silently. A trigger holds whoever writes.
- **Storing a level's grade as empty when it is its skill's own.** Its grade would then not be a key, and every reader
  would still need the rung to know it. The row holds the grade it has; a rung's grade moving moves the levels that
  follow it, and a level moved to another grade keeps it.
