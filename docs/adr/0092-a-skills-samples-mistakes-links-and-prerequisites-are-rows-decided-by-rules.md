# 0092 — A skill's samples, mistakes, registry links and prerequisites are rows; three decisions taken by rules

Date: 2026-10-21
Status: proposed
Goal: goals/b3-samples-mistakes-prerequisites.yaml

## Context

B3 of the backend plan (ADR 0084, BUILD-ORDER.md). Four things a skill names were never checked by the database: the
examples inside a level's words and a card kind's `kind`, the mistake codes in `skill_set.misconception_codes`, the
registry skills in its rung's `skill_codes`, and what comes before it, which was written nowhere. The decisions draft
(docs/drafts/b2-b4-decisions.md, B3-1 to B3-3) left three calls to Achal. Nimish, 2026-10-21: no dependency on Achal;
decide each by a rule a test can check. Achal may correct rows later; that is an update to rows, not a blocker.

## Decision

1. **Four tables, each code a key.** `skill_level_sample` (a key into `skill_level`, and into `question_format` for a
   card kind's example), `skill_mistake` (a key into `misconception`), `skill_registry_link` (a key into the registry's
   `skill`), `skill_prerequisite` (two keys into `skill_set`, never itself, never round in a circle).
2. **The lists stay what is written, the rows mirror them** (as ADR 0087 does for levels). The website, the loader and
   the engine (`spec.apply_computed`, `_store`) still write the lists; triggers keep the rows equal, whoever writes, and
   refuse a list that names a mistake or registry skill that is no row. `engine links check` compares the two.
3. **A mistake row per operation it shows in.** `misconception` is keyed by code and operation (M_WRONG_OP has five
   rows). Evidence names a mistake by code alone, so a skill naming a code links every row of it. A key on one chosen
   operation would have to guess which; a key on the code alone does not exist.
4. **B3-1, a level's examples.** The text after the words' last colon, to the end of that sentence, cut at ", " and
   "; "; numbers written in a row ("5, 10, 15, 20, □") are one example; a piece is a sample when it is written in signs
   (+ − × ÷ = ≈ < > ○ □, no word but a remainder's "r"). A piece in words ("56 × 3 = 1518 found wrong", "and why") stays
   in the words only. The words are never changed. The rule is SQL in the migration (so a person's edit re-splits at
   once) and Python in `engine/checks/links.py`; the two are compared on every level. On the seed: 240 samples on 114
   levels, 11 card examples, 58 levels keeping a piece in words (`engine links check --words` lists them for Achal).
5. **B3-2, the division mistakes.** Kept on a skill when a question its levels draw asks a division and the mistake's
   own rule (the engine's predictor, `spec.known_misconceptions`) computes a wrong answer on it. All 8 on
   Multiplication facts pass: its Advance level's fact family ("10 × 3 = 30. Use it to finish these facts.") asks two
   divisions, and each mistake computes a wrong answer on them. The four column mistakes are not division mistakes;
   they are computed on its 2-digit facts (11 × 12) and stay. "Multiplied instead of dividing" is one of the five rows
   of M_WRONG_OP, a code computed on Multiplication facts as "added instead of multiplying"; the code stays, and which
   row's words a page shows for it is the page's choice, made when the readers move onto these rows (not in B3). Six links fail and are removed by the migration and the
   seed: M_DIV_TENS_ZERO_EXTRA from DIV.3D1D, MD.EQUALITY and MD.ESTIMATE; M_DIV_QUOTIENT_ZERO_DROPPED from MD.EQUALITY
   and MD.MENTAL; M_DIV_TENS_ZERO_LEFT from MD.EQUALITY. Each stays on DIV.TENS, where it is computed. Marking reads
   no skill's list (it marks from each question's own boxes), so no answer is scored differently.
6. **B3-3, what comes before.** A skill comes after every skill of its topic on the nearest grade below its own: 167
   rows, drafted in `supabase/seed/skill_prerequisites.json` and inserted by `engine load` only while the school has
   none, so a prerequisite a person removes stays removed.

## Rejected

- **"Each skill after the one before it on the ladder"** (the draft's wording). The ladder's positions cannot order the
  skills: 26 of the 46 rungs have no `ladder_order`, and those that do put Grade 2 mental strategies (R7) before Grade 1
  addition (R19). Grades are the order the ladder does hold for every skill.
- **Removing the 8 division mistakes from Multiplication facts because the skill multiplies.** The rule asks whether
  the skill's questions ask a division, not what the skill is called; its fact family does, and a child who drops the
  zero of 30 ÷ 3 there makes exactly that mistake.
- **One mistake row per code with a chosen operation.** Which operation would be a guess for the five codes written for
  several operations and none for all (M_FACT_PM1, M_TIMES_AS_MORE…).
- **Splitting a level's words into a learning objective and samples, and storing the rest as the words.** The words are
  what a person reads and edits, and B1's rows mirror them; the samples are read from them, never cut out of them.
- **Moving the readers onto the rows now.** BUILD-ORDER's B3 asks for the rows and their keys; the readers move with the
  writers, one deploy before the lists go, as for levels.
