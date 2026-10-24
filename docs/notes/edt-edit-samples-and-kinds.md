# edt-edit-samples-and-kinds: an educator changes a skill's samples, kinds and words

Nimish, 2026-10-24, on an English skill's page: "What happens if he wants to make any changes there? … Is that capability
here, or is it just blue? What does 'change the words first' do? It should simply have the capability to edit the skill,
where the nature or the description of the skill can be changed. At the same time, a separate set of questions can be
generated. That is not here, right?" Goal: `goals/edt_edit_samples_and_kinds.yaml`. W1, step N1 (skill sets, approved by
a person). Making a new set of questions is the next job, not this one.

## What changed

- **One additive migration**, `20261212090000_an_edited_sample_keeps_what_it_replaced.sql`: two ledgers the database
  refuses to change (`internal.forbid_change`), `english_sample_edit` (one saved version of one sample, the sample it
  replaced, who, when; a removal is a version) and `skill_level_kind_change` (a kind added to or taken from a level, who,
  when), and a view `english_sample_now` (the newest edit, else the seed's sample). No existing table, column or row
  changes. `english_sample` stays the seed's: `engine load` upserts it on every deploy, so an edit there would have been
  overwritten by the next deploy.
- **Engine checks, code only** (`engine/w1_bank/english_check.py`, `english_wrong.py`, `english_words.py`), ported from
  `research/english_check.py`, `english_samples.py`, `english_wrong.py`, `english_spelling.py`: each kind's shape (a
  code-checked kind has one right answer among its options or gaps); each wrong answer differs from the right one and
  the others, fits the kind and names one of the skill's mistakes; British spelling (the pinned en_GB Hunspell
  dictionary, via `spylls`, fetched once into `data/`, refused if its fingerprint differs); the school's words (the rule
  moved from `tests/test_school_words.py` to `engine/core/school_words.py`, which the test now reads); an open kind needs
  its rubric and what a right answer does; the level's own rule (how many options, words, letters). Every fault is a
  sentence a person reads, by field. Not ported: working the answer out again by `worked_out`, which an edit does not
  carry.
- **Engine edits** (`english_edit.py`, `english_form.py`, routes in `engine/api/routes/samples.py`): save, add, remove a
  sample; add a kind (approved, with three samples that pass, saved together or not at all) or take one off (a level keeps
  one). Each withdraws that level's approval and no other. A Maths skill is refused in words. The loader no longer brings
  back a kind a person took off.
- **The skill page**: under each English level, each sample has Edit (the form opens in its place: passage, what the
  child is told, the sentence, options or columns, the right answer, other answers taken, each wrong answer with a
  pick-list of the skill's mistakes), Remove (while the kind keeps more than three) and Add a sample; the level lists its
  kinds with Take off and an Add-an-approved-kind choice that opens the three sample forms. A refused save shows each
  fault beside its field and keeps what was typed. A sample shows who changed it and when, and how many earlier versions
  are kept. The link "Change the words first" now says what it does ("Change the description and each level's
  sentence"), each level has "Change this level's sentence", and a Maths skill says why its questions are not edited.
- **Found and fixed at its cause**: saving the words on main kept every approval (the trigger keeps a level approved when
  only its words change) while the page said "The new words wait for approval". `saveWords` now withdraws the levels whose
  sentence changed, and every level when the description or name changed. And an approval of a level now lands only if
  its samples and kinds did not change after the page was opened (the form carries the time it read).

## Decided (by this session, for Nimish)

- Edits in their own ledger beside the seed's rows, not new columns or overwrites (deploy safety, history by construction).
- Who may edit: whoever may take `skill_drafts` ("Changing a skill"), the same as the words page.
- The kinds a level may be given: approved once, not observed, and asked by some level of the same subject.
- Spelling dictionary fetched at first use rather than committed (third-party data, 1.2 MB); if it cannot be fetched the
  save is refused in words, never stored unchecked.
- gstack's install was refused by this session's permission check; the reviews ran with Playwright and the repo's skills.

## Verified

On a database built from this branch alone (`bin/testdb fresh`, Postgres 16 in this sandbox, 102 migrations), the website
and engine reaching it as `app_web` and `app_engine`, 2026-10-24:

- Tests first: `tests/test_english_check.py` and `tests/test_english_edit.py` written before the modules (collection
  failed: no module). Now `pytest tests/test_english_check.py tests/test_english_edit.py` → `37 passed`; among them every
  one of the seed's 2,499 samples passes the engine's checks, and every form round-trips into the stored shape.
  Coverage of the new engine code 92% (`--cov`, per file 88–100%).
- `bin/engine done edt_edit_samples_and_kinds` → every sentence `PROVED`, every criterion `PASSED` (engine `94 passed`,
  `load --check` `unchanged on a second run`, browser `17 passed`, `tsc` clean, `bin/check` `31 passed`); `NOT DONE`
  only for what is not live: not on main, and live did not answer from here.
- Every browser spec: `CI=1 npx playwright test` → `396 passed, 1 flaky` (u50, a printed question's picture, passed on
  its retry; it opens no skill page). After the review's changes: u55, u54, u53, e0, u23, u28, u17, u5 → `28 passed`.
- `bin/engine ratchet --base origin/main` → `every baseline held or tightened`. `engine/checks/rules.json` written again
  from the local copy (`bin/engine live rules --write`), the two ledgers' rules only.
- Existing tests changed on purpose: u23, u53, u54 read the link's new words; `tests/test_school_words.py` reads the rule
  from the engine and leaves its file out.
- Reviews: `/code-review` (10 findings: 8 fixed, among them the word list the server could not see and approvals landing
  on a change made after the page was opened; 2 kept and said in the PR) and `/simplify` (four reviewers; the shared
  kinds list `level_kind_choice`, one stale-approval rule, one ledger insert, a cheaper view, fewer queries). gstack's
  install was refused by this session's permission check.

## Handoff

- **Live:** nothing until the merge. Before it: the rehearsal on a copy of live (`rehearse update-live` on this branch).
- **Next:** making a new set of questions (prompt rows with an eval score, ADR 0006 amended, these checks on the output).
- **Blocked:** nothing.
