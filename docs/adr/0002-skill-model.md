# ADR 0002 — Three levels: registry skill → rung → case tags

Date: 2026-09-16. Status: accepted.

## Decision

Every item carries a registry `skill_id` (from the school's 244-skill CSMAP), a `rung_id`
(R1–R14 ladder), and `tags` derived by code from the generator's parameters using the team's
*Addition & Subtraction Assessment Skill Taxonomy* §12 dimensions. No fourth vocabulary.

## Why

- The registry is what the rest of the Learning OS joins on (report lines, activities,
  objectives). Results that do not land on a registry id are invisible to the child graph.
- The rung is what a teacher reasons in: it is the level (L−/L0/L+), the blueprint key, and the
  unit of the Monday card. The taxonomy's own §13 progression maps onto it.
- The taxonomy's case tags are what guarantee coverage ("3-digit + 1-digit, horizontal, carry" is
  never accidentally missing) and what item statistics should be keyed on. The document's own
  rule — store dimensions as tags, generate by combination, do not hard-code topic names — is
  adopted verbatim.
- Deriving tags from generator parameters means they are never typed, never wrong, and free.

## Rejected

- **Invented difficulty levels (basic / intermediate / advanced) per objective**, as the first
  brief asked. Creates a parallel vocabulary; the Drive audit found three unreconciled taxonomies
  already.
- **Mockup-style ids (`ADD.R1`).** Readable, but not registry ids; they would fork the data.
- **Using the taxonomy's A01–A72 case codes as skill ids.** Too fine for a teacher and too coarse
  for the registry; as tags they serve both.

## Consequences

`rung.milestone_id` is nullable because the registry lacks G3 3-digit / across-zero subtraction
and any G4 content ladder. A coverage report lists those gaps; changes go to Akanksha through the
Skill Map Review, not from this repo.
