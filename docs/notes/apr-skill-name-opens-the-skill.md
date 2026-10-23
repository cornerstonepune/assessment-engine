# apr-skill-name-opens-the-skill: a skill's name opens the skill

Nimish, 2026-10-23, on Approve the skills: "shouldn't this page have a link that opens the skill in detail - coz the
questions associated with each level of difficulty and all needs to be down too. I can't click on any of these skills and
deep dive in." Goal: `goals/apr_skill_name_opens_the_skill.yaml`. Web only: no migration, no table, no prompt. W1 screens
(Curriculum / approve), beside the C slices of the 22 Oct scope.

## Verified

- Approve the skills (`/skill-sets/approve`): the skill's name in each row is a link to `/skill-sets/<code>`; the buttons and
  "Change the words first" are as they were. The skill page already held each level, its real question and its count linking
  to the library filtered to the skill and level (`/library?set=…&difficulty=…`).
- Skill page, for a draft: the button now reads "Approve, as <name>" and the link "Change the words first" (the list's
  words; an approved skill keeps "Change the words"). Per-level approval is the existing `level-approval.tsx`, not copied.
  English (no bank questions): each level says "No questions yet: English questions are made after this skill is approved and
  linked." and shows no count.
- Curriculum: table rows already linked each skill; the two lists that named a skill in plain text (the topic's skills, and
  the "Not taught yet" panel) now link it (`topics.tsx`; `Topic.skills` is `{code, name}`, one reader).
- Failing first: `tests/u53-skill-name-opens-the-skill.spec.ts` with the page changes stashed: 1 failed (no link on the row);
  with them: 3 passed (1440 px: Maths and English draft each opened from the list by click and by keyboard; Curriculum row).
- The eight older specs that looked for the button "Approve as written" now look for "Approve, as …" (e2e, s2-skill-map,
  u13, u27, u32, u49).
- Older specs on a `bin/testdb fresh` copy (Postgres 16 on this sandbox): u12, u17, u19, u23, u27, u32, u13, u49, u42, u5,
  u51, e0 and e2e pass; s2-skill-map passes at a 240 s limit (its default 30 s timed out on this slow copy while it fetched
  every link). `npx tsc --noEmit` clean.
- Before / after (desktop 1440 px; PNGs are not committed, `*.png` is ignored): before, the skill's name on the approve list was
  plain text and nothing in the row opened the skill; after, the name is a link. The skill page for an English draft shows
  its four levels, each with the approve button, its words, how it is asked and the "No questions yet…" sentence.
  Seeded test rows only (`APR_SHOTS=<dir>` makes the spec write them).

## Handoff

- Not changed: the Curriculum table's skill rows (already links), the library, the engine.
- Not live until merged and deployed; the manual check is in the goal.
