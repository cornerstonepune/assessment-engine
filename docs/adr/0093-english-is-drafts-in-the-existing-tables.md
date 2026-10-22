# 0093 — English is loaded as drafts into the tables that exist; what they cannot hold waits

Date: 2026-10-22
Status: proposed
Goal: goals/e0-english-in-the-system.yaml

## Context

BUILD-ORDER "E0" (Nimish, 2026-10-22): the English Grades 3–4 content of PR #254 and #272 goes into the system, as
drafts in the existing tables, for the English educator to review on the Curriculum page. No new table or structural
migration: the schema track owns tables, one slice at a time.

## Decision

1. **Loaded, from `supabase/seed/english/`, by `engine load`** (`engine/core/english.py`): the subject, 8 topics, 109 skills
   in `skill_set` (insert once, then the educators'), their 436 levels (the database makes `skill_level` from the skill's
   `difficulty`), 15 kinds of question in `question_type`, 833 level × kind links, 340 mistakes in `misconception` and
   405 `skill_mistake` links (made by the database from the skill's codes), 115 prerequisites. Nothing is approved by the
   load: no level confirmed, no kind approved, so `drawable_item` offers no English question to a paper.
2. **Read in the tables' own words.** `subject.mark_mode` allows `lookup` or `rubric`: English is `lookup`, marked kind by
   kind. `misconception.detectable_by` allows four words: `model` and `educator` become `teacher`, which is who reads an
   open answer while a kind is new. `misconception.op` is `any`. A skill's rung is its own code: `skill_set` still keys a
   skill to one rung (B4 folds it in).
3. **The checks that are about a bank are about skills that have one.** A skill none of whose levels carries a `check`
   draws nothing from a bank: `engine audit` no longer asks it to be approved, to make a question or to meet a bank's
   target, and a mistake only such skills watch for is not asked to have a generator. The same checks still ask every
   maths skill. `references.orphans` compares bands that share a `check` only where there is one.
4. **The Curriculum tree has a subject row for each subject** of a grade (it picked the first subject by code, which
   would have named every maths skill "English"). Its ids are `G3/NUM`, `G3/ENG`.
5. **A skill with no bank questions is read from the rows**: how each level is asked, a person checks every answer of an open
   one, the mistakes it watches for in words. A way of asking is approved once on the skill's page (`question_type_approval`),
   in the person's name and the date, for every skill that asks it that way; a level is approved as maths levels are.
   Every member of staff may (ux9c).
6. **bin/testdb approves what live has approved**: maths only, so English stays drafts on the copy as on live.
7. **The site opens on the subject that has approved skills** (`lib/choices.ts`): subjects were listed by code, so English
   (`ENG`) came before Maths (`NUM`) and would have been what Today and every page opened on for anyone who had not chosen,
   with nothing approved in it. A subject with approved skills now comes first, then by code; once English has approved
   skills too, the code decides again. Nimish decides which subject the site opens on, if not this.
8. **One grant, in a numbered migration** (`20261203090000_the_website_may_add_an_approval_of_a_kind.sql`): the website's
   role could not insert into `question_type_approval` ("permission denied"), though B2's migration says the website may
   add an approval. CI runs the website as that role and caught it; a run as the table's owner does not. It is a permission,
   not a table: nothing in the schema changes shape.

## What waits (not loaded, not faked)

- **A sample's right answer and its wrong answers, each naming a mistake** (2,499 samples). `skill_level_sample` holds one
  line of text, and its triggers re-make a skill's rows from the level's words, so nothing stored there would last. It
  needs a table of its own with real keys to the kind, the level and the mistake: the schema track. No slice of BUILD-ORDER
  names it (C1 is the nearest: a question's skills as keys); Nimish decides.
- **Send back with a reason.** Approval records hold approvals only. C5 (one approval list for everything new).
- **The three observed kinds and the 56 observed skills**: `question_type.reaches` allows printed, read aloud and drawn. C2.
- **Passages, rubrics, objective coverage, the not-on-paper list**: no table.
- **A fragility, named:** writing any question type clears every level's links to be made again from the bank (B2's trigger,
  `skill_level_question_type_sync_all`), and the bank holds no English question, so the English links vanish until the next
  `engine load`, which puts them back (tests/test_e0_english.py). A new type written by anything but a load would drop them.
  The cause is that trigger's assumption that every level has a bank; it is a migration, so it waits for the schema track.

## Rejected

- **Storing a sample's answer and wrong answers as JSON in `skill_level_sample.sample` or `question_format.kind`.** It would
  show on the page and be a blob again: the wrong answer would not be a key to its mistake (ADR 0084), and the trigger would
  delete it on the next edit of the skill.
- **Loading samples as `item` rows.** The bank is generated; `item.source` allows `generated` and `legacy`, and a draft in it
  is counted by every coverage check and refilled over.
- **Mapping `model` to `explanation`.** That says the child explained it. `teacher` says a person reads it, which is true.
