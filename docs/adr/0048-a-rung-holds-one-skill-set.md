# ADR 0048 — A rung holds one skill set, and the database says so

**Status:** accepted (2026-10-09, slice M0c of BUILD-ORDER "Inserted now: multiplication and division")
Goal: goals/md0c-a-skill-set-is-read-as-itself.yaml

## What happened

Measuring before M0c, a read-only sweep found about twenty-four places that read a skill set through its rung: the
graph's own functions, the class card, the child and parent reports, the website's children, report and curriculum
queries. Each joins `skill_set.rung_code = …rung_code`. Nothing kept a second skill set off a rung, so two on one rung
would each be read as whichever row came last. The seed has always held one per rung (28 skill sets, 28 rungs), so no
report is wrong today. Multiplication and division add seventeen skill sets, which is when it would start to matter.

## Decision

A rung holds one skill set, enforced by a unique index on `skill_set (tenant_id, rung_code)` (migration
20261027090000). Every reader that finds a skill set by its rung is then right by construction. A new skill set gets a
rung of its own, as every row in `supabase/seed/rungs.json` already does.

## Rejected

**Re-keying every reader by skill set code.** It changes about twenty-four queries across the engine, the graph's SQL
functions and the website, for no difference in what any reader shows while one skill set sits on each rung. It would
also leave the rung, which evidence and child_skill_state are keyed by, able to mean two skill sets at once, so the
graph would still need the one-per-rung rule to place an answer. The invariant is the cause; the readers were never
wrong under it.

## Consequences

- A seed that puts two skill sets on one rung fails at `engine load`, before anything reads it.
- The live migration fails, loudly, if live ever held two on one rung. The seed never has.
- A skill set that replaces another (a seed row's `replaces`) takes a rung of its own. `engine load` inserts it before
  `engine bank rehome` deletes the one it replaces, so on its predecessor's rung the load would be refused. M2's
  multiplication skill sets, replacing `MUL.1D`, each get a new rung.
