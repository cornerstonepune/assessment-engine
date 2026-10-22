# ux9b-regroup: the school's word is "regroup"

Nimish, 2026-10-22, on the audit's question D1 (`docs/notes/ux8-every-screen.md`): "regroup". Goal:
`goals/ux9b-regroup.yaml`.

## Verified

- No screen, string the engine prints or writes, or seed row a person reads says "carry", "carrying" or "borrow" for a
  column passing ten; a parent report saying it is refused by `parent_check`:
  `cd packages/engine && uv run pytest -q tests/test_school_words.py` → the four file checks failed on main's code
  first (4 failed), and pass on this branch.
- Rewritten: 152 taxonomy case words, 33 level words and objectives, 22 mistake names, descriptions and hints, 13 case
  dimensions, 18 registry lines (the maths skills, their milestones, 8 report item titles, one example), a rung, a
  config line, two drafted questions, the learned mistakes' words and the taxonomy page's §5 heading. Codes untouched.
- Changed with them, since each must say what the seed says: the drafted taxonomy for Achal (`docs/design/`), one
  goal's line that drafted a question for him, and the parent report gold's drafts and facts (a draft a person found
  right would now be refused for "carry", so it says "regroup", as the facts it was written from now do).
- Left as they are, on purpose: a van or a child carrying things (English), past papers as printed (`seed/papers`), the
  other gold files (what a person once wrote, scored against), and the prompts (words to a model; its report is
  checked in code).

## Handoff

- **Live:** nothing until merged and deployed. Migration `20261130090000_the_school_says_regroup.sql` replaces level
  words and objectives where they are still the seed's old words, and renames 8 report item titles (their key).
- **Manual, once deployed:** the query in the goal's `manual`, for any level reworded on the site since the seed.
- **For Nimish:** subtraction still says "exchange" (the school's own word in CLAUDE.md, and not named in the decision).
