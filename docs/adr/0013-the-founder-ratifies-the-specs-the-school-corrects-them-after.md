# 0013 — The founder ratifies the specs; the school corrects them afterwards

Date: 2026-09-19
Status: accepted

## Context

W1 gate 1 asks for two things: every rung has a skill-set spec (a command proved that on
2026-09-19), and every spec is `ratified` — a named person has read it and stands behind it.
N1 in `docs/sources/assessment-workflow-v1.md` puts that signature on Aseem, after Neha and
Achal correct the drafts.

All 17 specs sat at `status = 'draft'` for two days. Nothing downstream of W1 can be built
honestly while the input to it is unapproved, and the three open questions the engine surfaced
(the pedagogy reviewer's objection to mixing formats inside a band, one gold-set disagreement,
and the G1 floors) are pedagogy, not engineering — they do not get answered faster by the repo
waiting.

## Decision

Nimish ratifies all 17 specs himself, by command, with his own name on every row:
`engine ratify --by "Nimish Shah"`. Gate 1 closes on that signature. Neha, Achal and Aseem
correct the specs afterwards, in the screen, as the ordinary path — and because a content edit
withdraws ratification automatically (trigger `skill_set_version_on_change`, ADR 0012), any spec
they change returns to `draft` and needs a signature again. The signature therefore always names
the person who read the exact words that are live.

`ratified_by` holds a person, never a role and never "the system", so the provenance chain
answers "who said this question was fair" with a name.

## Alternatives rejected

- **Wait for Aseem.** The honest sequence, and it is what N1 says. Rejected for now because it
  blocks W2 on other people's calendars while the specs are already the engine's own drafts of
  documents the school wrote; the correction path stays open and un-ratifies what it touches, so
  nothing is lost by signing first.
- **Ratify in the app, one screen at a time.** That path exists and stays the normal one for a
  single spec. Seventeen clicks to close a gate is not a command, and gate discipline
  (`BUILD-ORDER.md` rule 2) wants a command with an output.
- **A `system` or `founder` literal in `ratified_by`.** Cheap, and it destroys the only thing the
  column is for.

## Consequences

- Gate 1 is closed, and W1's six gates are all closed. W2 opens.
- Every ratification is per-version: the moment a teacher edits a band's words, that spec is a
  draft again and its items keep the version they were made from.
- The three open pedagogy questions are still open. They are recorded in `HANDOFF.md`, and
  ratification did not answer them.
