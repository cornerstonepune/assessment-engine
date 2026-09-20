# 0017 — Evidence that matches no known skill is held, named later, and counts retroactively

Date: 2026-09-20
Status: accepted

## Context

Nimish, 2026-09-20, on the Olympiad booklets: *"structurally, we'll have some of these kinds of
inputs coming in, like physics, science, Olympiads, and other exams also. They might not very
clearly attach themselves to a certain skill set in that table, but somehow we need to still figure
out a way that they become a part of the evaluation of the child."*

The corpus already contains this. Seven SOF Olympiad booklets, 66 pages, 35 multiple-choice
questions each, and the Grade 3 items are mostly not addition or subtraction: *"4 groups of ___ fish
can be formed"*, *"if camels H and L are removed, which camel is second to the left of the third
from the right?"*, a symbol-substitution puzzle, a balance-scale weight problem.

The registry can absorb more of this than expected. It holds **244 skills across 14 domains**, and
every Olympiad item examined maps to one that already exists — `NUM.GEO.03` position and direction,
`NUM.PAT.02` patterns and sequencing, `NUM.MEAS.01` calendar, `NUM.MEAS.03` mass. But only **8 of
those 244 skills sit on a rung**; the other 236 are named with no ladder underneath them.

And one column makes the whole question moot today:

```
select column_name, is_nullable from information_schema.columns where table_name = 'evidence_event'
  skill_code | nullable=NO
  rung_code  | nullable=NO
```

**An observation that maps to no known skill on no known rung cannot be stored.** Not stored badly —
there is nowhere to put it. It is dropped, and the child gets no credit for work they did.

## Decision

Evidence whose skill is not yet known is **stored anyway**, named later by a person, and counts from
the moment it is named — including for papers sat months earlier.

1. `evidence_event.skill_code` and `rung_code` become nullable. A row with a null skill carries what
   the engine believes the item tests, in its own words, plus its subject and its source capture.
2. The unnamed pile is **reported, grouped by what the engine thinks it tests, across children** —
   the same instrument `engine bank unclassified` already provides for unnamed mistakes (ADR 0012),
   pointed at skills instead.
3. A person resolves each group: map it to an existing skill, or approve a new `skill` row. The
   registry is rows (CLAUDE.md rule 1), so it grows by insert, never by a code change.
4. **Naming a skill makes the old evidence count.** Ring B is derived and rebuildable from Ring A at
   any time, and evidence is append-only (rule 4) — so nothing was lost, and `engine graph` places
   September's evidence on a skill named in November without re-reading a single page.
5. Non-maths papers arrive as `subject` rows with their own verifier (ADR 0009). Where code cannot
   check an answer — most of science — the item routes through the human gate, exactly as the
   R7/R11/R13 rungs already do rather than inventing a numeric check for a judgement call.

Until a skill is named, the evidence is still part of the child's evaluation: what they sat, how
they did, and what the engine observed, shown as *other evidence* on the child's page.

## Alternatives rejected

**Force-fit to the nearest known skill.** A circuits question filed under `NUM.PAT.02` corrupts the
child's pattern score and every analysis downstream, and it is unrecoverable — once filed, nothing
records that it was a guess. A wrong label is worse than no label, because it is invisible.

**Discard what does not map.** This is today's behaviour, reached by accident through a `NOT NULL`
rather than by choice. It violates rule 4 in spirit: the child did the work and the system threw it
away. It also guarantees the registry can never learn what it is missing — the gaps are exactly the
evidence that is being dropped.

**Wait for a complete registry before accepting these papers.** The registry is never complete; that
is why it is rows. Waiting means the pilot discards real evidence for as long as it takes, and the
demand signal for which ladder to build next is precisely what is being discarded.

## Consequences

- A migration makes two columns nullable, and `engine audit` gains an invariant that a row with a
  null skill carries a proposed description instead — so "unnamed" can never mean "empty".
- The Olympiad's real value is as **a map, not a dig**: 35 questions over ~20 skills is 1–3 per
  skill, and `state.min_events` is 3 with `min_observers` 2, so a booklet alone will rarely place a
  skill on the graph. What it does say is *which of the 236 unladdered skills the children are
  actually failing*, which is the evidence for what to build after addition and subtraction.
- Olympiad items are entered as question + correct answer only (Nimish, 2026-09-20), not with their
  distractors. A bare circled option therefore yields right/wrong and no misconception; claiming one
  from it would be a fabricated diagnosis.
