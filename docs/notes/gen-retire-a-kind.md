# gen-retire-a-kind: an educator stops a kind of question, and can use it again

Nimish, 2026-10-26: "When we have the capability to edit, the educator also, today, does not want certain types of
questions. They should be able to delete those kinds of questions from the bank itself." Goal: `goals/gen_retire_a_kind.yaml`.
W1, steps N1 (skill sets, approved by a person) and N2 (the bank). Part A of two; Part B (making questions from an
educator's sample) is the next PR. Decision record: ADR 0096.

## What changed

- **One additive migration**, `20261214090000_a_kind_stopped_is_kept.sql`: `skill_level_kind_stop` (a stop or restart of
  one kind at one level, who, when, and the codes of the papers it sent back for approval; the database refuses to change
  it), the view `kind_stopped` (the newest row says where a kind stands), and `drawable_item` (the one view every paper
  draws from) leaving a stopped kind out at its level. No existing table, column or row changes.
- **`drawable_item` is about ten times faster**: the kind of each question is worked out once (`offset 0` in a lateral),
  not in every test that reads it. Same rows (an `except` both ways on a fresh copy: 0 and 0); 57 ms against 606 ms.
- **Engine** (`engine/w1_bank/retire.py`, on N2 in `workflows.json`; routes in `engine/api/routes/samples.py`):
  `touches` counts what a stop would touch and writes nothing; `stop` and `start` write a row per level, send back the
  approved papers not yet given (this week's or later, no "given" word, nothing read), and withdraw that level's approval
  (`english_edit.withdraw`, renamed from `_withdraw` so both use one). Refused in words: no person, a kind not asked
  there, already stopped, or a level that would be left with no kind in use. `question_types.why_not` names a stopped kind.
- **The skill page** (`kind-stops.tsx`, `stop-actions.ts`): a panel "Kinds of question in use", a table grouped by level,
  each kind "in use" or "stopped". "Stop using this kind of question" opens a confirm step that says how many questions
  and past papers it touches, that nothing is deleted, which approved papers not yet given go back for approval, and that
  the level draws no new paper until approved again; it offers "Stop it at every level instead" and "Keep using it".
  A stopped kind has "Use it again". Who may: whoever may change the skill (`skill_drafts`), as the edits of #323.

## Decided (by this session, for Nimish)

- "Not yet given" is: approved, this school week or later, no "Given on" for it, nothing read from it. An older paper
  never marked given is treated as given (it almost certainly was) and is left alone.
- A restart also withdraws the level's approval: it changes what the level draws, as a stop does.
- Withdrawing the level's approval stops the whole level drawing until it is approved again (that is what approval means
  here, as for any edit). The confirm step says it in words.

## Verified

On a database built from this branch alone (`bin/testdb fresh`, Postgres 16 in this sandbox, 105 migrations), 2026-10-26:

- Tests first: `tests/test_retire_kind.py` collected with `cannot import name 'retire'` before the module; now 7 passed.
  Two found on the way and fixed at the cause: withdrawing a level's approval stops the whole level drawing until it is
  approved again (the tests and the confirm step now say so), and the lookup query compared every question with every
  other (rewritten).
- `bin/engine done gen_retire_a_kind` → 7 of 7 sentences `PROVED`, 4 of 4 criteria `PASSED` (engine `51 passed`,
  browser `11 passed`, `tsc` clean, `bin/check` `32 passed`); `NOT DONE` only for what is not live: not on main, and
  live did not answer from here.
- The tests of every area the change reaches (approvals, English edits and checks, focus papers, hand-outs, library,
  maker, packs, question types, rules, roles, the week, the loop): `273 passed, 2 skipped, 1 failed`; the one,
  `test_e0_english` loading twice, failed while a second run loaded the same copy at once, and passes alone (`1 passed`).
  The whole suite did not finish here inside its hour; CI runs it.
- Browser: u64, u55, u54, u23, u53, e0, u28 → `18 passed`. The first run broke u54, u55 and e0 (the panel's per-level
  headings had the levels' names) and the stop action refused a kind named by a printed format (`bare_sum`); both fixed.
- `drawable_item` the same rows as before (an `except` both ways: 0 and 0), 57 ms against 606 ms.
- `engine/checks/rules.json` written again from the local copy (`bin/engine live rules --write --url` the copy): the new
  table's three rules only.

## Handoff

- **Live:** nothing until the merge. Before it: the rehearsal on a copy of live (`rehearse update-live` on this branch).
- **Next:** Part B, making new questions from an educator's sample (prompt row, its eval, ADR 0006 amended, #323's checks
  on every question a model writes).
- **Blocked:** nothing.
