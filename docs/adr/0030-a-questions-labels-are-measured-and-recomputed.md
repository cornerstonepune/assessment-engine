# 0030 — A question's labels are measured from the question, and recomputed when the rule improves

Date: 2026-09-22
Status: accepted (step 8a, `BUILD-ORDER.md`)

## Context

`item` is Ring A: rows are appended or approved, and a batch job never edits them. But two of its
columns are not facts about the question — they are readings of it. `tags` is the taxonomy's §12
dimensions measured by `assess/tags.py` from the numbers, and `skill_codes` was meant to be the
skills the question uses. `bank.fill` copied `skill_codes` from the rung instead, so on 2026-09-22
10,319 of the 12,331 generated questions carried a skill they do not use — every 3-digit addition
also "subtraction" (its rung, R9, names both), every budget problem "word problems + money" and never
the adding and subtracting it needs (ADR 0023).

## Decision

- A question's derived labels are a pure function of the question: `skill_codes` from
  `assess/skills.used` — its operations and its kind, each mapped to a registry skill by a config row
  (`skills.by_operation`, `skills.by_kind`, `skills.by_symbol`), the rung's own skills only deciding
  which leads, so `skill_codes[1]` stays the question's own skill.
- `engine bank relabel` recomputes them for every generated question. It never touches the question
  itself — its numbers, words, answer and wrong answers — and never touches a question from an old
  paper (`source = 'legacy'`), whose skill a person gave it.
- `engine audit` holds the invariant: no question carries a skill it does not use.
- The same rule covers `tags` when the tag measurements improve (step 8e): recomputed, never hand-set.

## Why this is not an edit of Ring A

The question a child sat is unchanged, so every paper already printed and every answer already read
still points at the same question. What changes is the engine's reading of it — as when a paper is
entered again and re-read, which the repository already does without calling it an edit.

## Rejected

- **Leave the old labels and label only new questions.** Then the graph (ADR 0023) would count 10,319
  questions for skills they never used, for as long as those questions are in the bank.
- **Retire every mislabelled question and generate it again.** The same numbers under a new key
  would retire 1,123 worksheets and break the link from printed papers to the library, to change a
  label.
- **Store the labels per paper instead of per question.** The label is a property of the question,
  and every paper that holds the question would repeat it.
