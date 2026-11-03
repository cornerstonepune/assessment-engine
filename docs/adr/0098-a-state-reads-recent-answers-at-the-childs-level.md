# 0098 — A state reads recent answers at the child's level, and secure is re-checked

Goal: goals/gr1-state-from-recent-evidence.yaml

Nimish, 3 Nov 2026, from the learning-science review (cornerstonepune/teacher-os,
research/council-2026-11-03/learning-scientist.md §1). The rules that decide a child's state per skill and the next
paper's level had five defects, confirmed by reading the SQL:

- the next level pooled every answer at every level, all time (20 Easy right and 4 Medium wrong was 0.83, a move up);
- a repeating mistake was any code seen twice, ever, and never cleared;
- the share was all-time;
- "observers" counted papers, and an answer on no paper counted as an observer of its own;
- ready to move up meant six answers at 0.8: volume, not performance.

## Decided

- **The next paper's level** reads the last `next_sheet.papers` (2) papers at the child's current level only. The
  current level is the last one prescribed, else the level of the latest answers, else `level.usual`. Too few answers
  at the current level (a child just moved up) keeps the child there.
- **A level's state** reads its last `state.window_answers` (10) right-or-wrong answers.
- **A repeating mistake** shows in `state.repeat_min` (2) of them, and `state.repeat_clears_after` (3) right answers on
  later papers clear it.
- **Secure** needs `state.secure_min_answers` (6) answers, on `state.min_days` (2) school days, with the latest day
  at `next_sheet.promote_at`.
- **Re-check.** Until a paper `state.recheck_days` (14) or more later, at that level or a harder one, reaches
  promote_at too, the state is the new row `secure_to_recheck` ("secure, to re-check"). It is amber, worked on by the
  next paper, nearly secure to a parent, and never counted as secure.
- **Ready to move up** is re-checked secure with a harder level above. At the hardest level it is `secure`.
- **A skill's one state** (`child_skill_state`) is its state at the level of the child's latest answers, and the row
  now says which level (`difficulty`).
- **Observers** are school days for every kind of evidence. Distinct adults (`seen_by`, `state.min_adults` 2) apply
  only to evidence that names who saw it, which no written answer does.
- **A paper made before levels** (the historical papers, N3) has answers at no level. They count in the graph as a
  bucket of their own. They never set the next level: a child with only those papers stays at their current level.
  The first draft gave them the grade's start (`band_default`). The rehearsal on a copy of live (run 119) showed that
  would reset 60 levels the school had already set, for 12 children.

## Rejected

- *A moving average (EMA) instead of a window.* It is equally defensible: the review cites Pelánek & Řihák (2017). But a
  window is a count a teacher can check against the papers ("8 of the last 10"), and an EMA's weights are not.
- *A skill's one state as its highest secure level.* It would show green for Medium while the child fails Hard, hiding
  the level the child is working on.
- *Leaving a provisional secure as practising.* An educator could not tell a child who has just done well on two papers
  from one who is struggling.
- *Retiring `stretch_ready`.* The Friday card and the parent report group by it. Re-checked secure is the honest
  meaning it lacked.
- *Counting the adult who signed off a written answer as its observer.* That person did not watch the child. Requiring
  two would have taken secure from almost every child on live.
- *Treating a historical paper's answers as `level.usual`.* That would be a guess at a level nobody set.
- *The grade's start for a child whose answers name no level.* It throws away the level last prescribed (run 119).

## Not decided here

- The paper-maker does not schedule the re-check 14–21 days after a provisional secure. A child is re-checked only when
  a later paper on that skill comes their way.
- The review's "no demote-level result at any easier level" before secure was not in Nimish's list, and is not built.
