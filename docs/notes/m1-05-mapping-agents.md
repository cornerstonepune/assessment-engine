# M1-05 — agents that fill the gaps in the K2 curriculum map

W1, gate N1. Nimish, 2026-11-03: "one agent that develops for all the places where you don't have descriptions, the
right learning objectives, or the skill mapping … another validation agent is also needed". Goal:
`goals/m1-05-mapping-agents.yaml`. Live K2: 871 activities; 527 mapped by people (the **gold set**); 63 no objective, 3
no skill, 278 neither, 126 no level words; 0 of 746 objectives linked straight to a skill.

## How it works (built, run on recorded replies only)
- **Proposer** (prompt row `curriculum_map_propose` v1): one question per activity. It gets the activity's words, its
  gaps, the band's skills in the families people linked to its subject, and the 5 nearest activities people mapped
  (nearest = shared words, computed by code). It returns the skills, an existing objective code or new words, the level
  words, a confidence and a reason.
- **Code checks** (`map_check.py`, pure). Every code must exist in the band, and a skill's family must be one people
  linked to that subject. Nothing may be named twice or already linked, and level words go only where the sheet has
  none. Any problem rejects the proposal.
- **Validator** (`curriculum_map_validate` v1, a different model, never shown the proposer's reason): agree or
  disagree. It is asked only about proposals that passed the code checks.
- **Where a proposal goes.** A confident, agreed, checked skill or existing objective passes on its own. New words, a
  disagreement, confidence below 0.8, the 5% audit sample (drawn by code) and any kind whose audit people turned down
  too often all go to a person.
- **Objective → skill links are made by code, not a model.** An activity with one objective means that objective tests
  each of its skills; an activity with one skill means each of its objectives tests that skill. Two and two would be a
  guess, so none is made. (K2 objectives belong to one activity each, so "shared by ≥2 activities" would find nothing.)

## The ledger (migration 20261230090000, additive)
`curriculum_proposal`: one row per proposal, decided when it is made. A person's yes or no, an apply and a revert are
each a new row pointing back at it. The ledger is never edited; DELETE is revoked and a trigger refuses update and
delete (TRUNCATE is left alone). The three link tables gain `source` (person | machine) and `proposal_id`. P-09: every
link added or removed, by anyone, now goes into `curriculum_edit`, with who did it (the machine's apply is written as
`machine:<proposal> for <name>`).

## The eval: the bar comes before anything applies
20% of the gold set is held out, per subject (at least one each), chosen by a hash so every run picks the same ones.
Their links, their objectives and their part in which families fit are hidden. Code scores the auto-passed proposals
on two measures: every skill right (bar 0.90) and the share of people's skills found (0.85). It also scores the share
that passed on their own (0.60). All three are threshold rows and only proposals until Nimish confirms them.
**Objectives cannot be scored by agreement:** each K2 objective belongs to its own activity, so a held-out activity's
objective is new words, with no person's answer to compare. New objectives and new level words always go to a person.

## Commands (dry run unless `--apply --by <name>`)
`engine curriculum propose | review [--decide ID --yes/--no --by] | apply | revert ID --why`. `engine eval
curriculum_map` (model, on the box) and `engine curriculum eval --recorded <file>` both score against the bars. The
two prompt rows are **inactive** until a real eval meets the bars (rule 7), so until then `propose` refuses in plain
words.

## What runs where
This container has no model key: every agent reply in the tests is recorded. The real run happens on the box, where
`adapters/llm.py` holds the key: eval → DECISIONS-LOG → prompts made active → propose → review → apply.

## Seam for P-08 ("given a topic, the next objectives and how to teach them")
Not built. A new kind is a prompt row, a code check and a bar; propose, check, decide, record, apply and revert don't
change.

## Verified
- `uv run pytest -q tests/test_map_check.py tests/test_map_eval.py tests/test_map_ledger.py` → `22 passed`
- `bin/check` → `34 passed`; ruff clean
- the migration run twice on a local db built by `bin/testdb fresh` → no error
- `engine live rules --url <local>` → `0 rules held otherwise than the migrations make them`

## Handoff
- In flight: draft PR #365. Schema queue: #363 → #362 → M1-02 → this. After they merge: merge main, then regenerate
  rules.json (and config/data_register if they conflict) on a local db. Rehearsal not dispatched.
- Next: the real eval on the box. Open: the bars are not yet Nimish's. No data-register entry: the ledger holds no child.
