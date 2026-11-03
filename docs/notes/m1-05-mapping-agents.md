# M1-05 — agents that fill the gaps in the K2 curriculum map (design, not yet built)

W1, gate N1 (skill sets and the ladder). Nimish, 2026-11-03: "one agent that develops for all the places where
you don't have descriptions, the right learning objectives, or the skill mapping … another validation agent is
also needed, so we don't have to wait for manual input from teachers."

## The gaps (live K2, 871 activities)
527 have objective + skill (the **gold set**, made by people) · 63 skill, no objective · 3 objective, no skill ·
278 neither · 126 no level words · 0 of 746 objectives linked straight to a skill.

## 1. The roles
- **Proposer** (model, prompt row `curriculum_map_propose`). Reads: the activity's name, strand, objective text,
  materials, sheet words; the K2 skill registry for that subject; up to 5 nearest *gold* activities as examples
  (nearest by shared words, computed by code); the school's words list. Returns JSON:
  `{objective: existing LO code | new text, skills: [codes], level_words?: {0..3}, confidence 0–1, reason}`.
- **Validator** = code first, then a model. *Code* (no model, decides alone): every code exists; skill's family
  fits the activity's subject; band is K2; no link already present; no duplicate skill; level words only where the
  sheet has none; any code not in the registry rejects the whole proposal. *Model* (prompt row
  `curriculum_map_validate`, a different model from the proposer — `llm.py` already runs Claude and Gemini): sees the
  activity and the proposal, not the proposer's reason; answers agree / disagree + why.
- **Code before model where code can do it** (rule 11). The 0-of-746 objective→skill links are not a model job:
  on the gold set an objective and a skill already share activities, so code proposes "objective X → skill Y
  where they share ≥ N activities" and the same validator checks it. N is a threshold row.

## 2. The ledger (one new table, append-only)
`curriculum_proposal`: id, activity or objective code, gap kind (`skill`, `objective`, `levels`, `lo_skill`),
the proposal (json), proposer prompt version, validator prompt version, code verdict, model verdict, confidence,
status (`proposed → auto_passed | needs_person | rejected → applied → reverted`), the curriculum version it was
applied in, who/what (a person's name, or `machine:<prompt version>`), time. Never updated: a status change or a
correction is a new row pointing at the one before.
The link tables gain two nullable columns (additive): `source` (`person` default, `machine`) and `proposal_id`.
So every machine link can be listed, reverted (link removed + a `reverted` row) and the child's picture rebuilt.

## 3. The eval — the bar is set before anything applies
Hold out 20 % of the 527 (about 105, spread across the 12 families, fixed seed, saved as a seed file). The held-out
activities are **removed from the examples** the proposer sees — otherwise it copies the answer and the score lies.
The agents map them blind; code scores:
- skill: share of auto-passed proposals whose skills are all in the person's set (precision) and share that hit
  at least one (recall); objective: proposed code equals the person's code.
Bars are threshold rows (`eval.curriculum_map.*`). My proposal, to be confirmed: precision ≥ 0.90 and recall
≥ 0.85 on auto-passed items, and at least 60 % of items auto-pass (below that the agents save nobody time).
Nothing applies to the 341/278 until the recorded run clears every bar. Each gap kind has its own bar; a kind
without one never auto-passes.
**Limit to say plainly:** a newly *written* objective or new level words have no person's answer to compare
against, so they cannot be scored by agreement. Those go to a person in this version, always, until a sample a
person has judged gives them their own bar.

## 4. The person's part
One list, worked top to bottom on the curriculum page later (S6); a command now: every `needs_person`, every
low-confidence or validator-disagrees item, every new objective or level text, and a 5 % random sample of
`auto_passed` (the sample is drawn by code, the share a threshold row). A person's yes/no is a ledger row with their
name. If the sample's disagreement exceeds the bar, auto-pass stops for that kind.

## 5. What runs where
This cloud session has no model key: it builds and tests with **recorded replies** (fake activities, stub JSON).
The real proposer/validator run happens on the box, where the engine and `adapters/llm.py` hold the key, or in a
session Nimish supervises with a key. Order there: eval run → score recorded in `DECISIONS-LOG.md` → prompts
activated → `propose` on the gaps (writes ledger only) → `review` → `apply --apply --by <name>`.

## 6. The seam for "given a topic, the next objectives and how to teach them"
Not built (P-08 designs it). The seam: gap kind is a row-level word, the ledger takes any subject code, and the
proposer/validator/eval/apply loop does not know which kind it serves. A new kind is a new prompt row, a new code
check and a new bar.

## Build order (after the blueprint is accepted)
1. pure-code validator checks (tests first) · 2. eval harness scoring a recorded gold run · 3. migration
(additive, `internal.apply_conventions()`, DELETE revoked on the ledger, rules.json regenerated on a local db,
data_register entry) · 4. `engine curriculum propose | review | apply` (dry-run default, `--apply --by`) ·
goal `goals/m1-05-mapping-agents.yaml` with Nimish's words as `says:`.

## Open questions for the orchestrator
- Are 0.90 / 0.85 / 60 % the bars, or does Nimish set them?
- Should a new objective's text ever auto-apply in this version? I say no (nothing to score it against).
- `lo_skill` by code co-occurrence: is "≥ 2 shared activities" acceptable as the starting rule?

## Verified
Nothing built yet. Design only.

## Handoff
Design only, by order (Nimish via orchestrator, 2026-11-03): the whole blueprint is finished and accepted before any
new build slice. This note is input to blueprint chapter P-08. Build starts later on the orchestrator's word.
