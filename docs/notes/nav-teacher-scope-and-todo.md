# nav-teacher-scope-and-todo: top menu, a person sees their own, What needs doing and Teaching as tables

Nimish, 24 Oct 2026, on the live site after the UI wave (his words are in `goals/nav_teacher_scope_and_todo.yaml`).
Goal: `goals/nav_teacher_scope_and_todo.yaml` (`bin/engine done nav_teacher_scope_and_todo`). Website only: no migration, no
engine change except one ratchet check. W3, no gate moved: this is the educator's site over W2/W3's data.

## What was built

- **Top bar, no sidebar** (`components/shell.tsx`, `nav.tsx`, `lib/menu.ts`): the Cornerstone mark, five groups (What needs
  doing, Teaching, Assessments, Results, Setup), the search, a three-line menu button that opens every page of every
  group. A group's other pages are tabs under the bar. The mark is `public/brand/cornerstone-mark.svg` (from
  `origin/claude/brand-logo`), also the tab icon (`app/icon.svg`, the old `favicon.ico` is gone) and on sign-in.
- **A person sees their own** (`lib/viewing.ts`): the staff row holds `classes` and now `subjects` (the Staff page edits both).
  One class and one subject: no Class/Subject box. Every class, or two subjects: one "Viewing" control. A view, never a
  permission (`lib/access.ts` unchanged; every address still opens).
- **What needs doing** (`/today`, `lib/todo.ts`, `lib/queries-todo.ts`): a table, red/amber/green, grouped by subject then
  topic, one action per row. Teaching's "Mark a topic taught" and "Generate an assessment" rows are green.
- **Teaching** (`/taught`, `lib/topic-flow.ts`, `lib/queries-teaching.ts`): a tab per subject, a table of topics, each with
  its flow per class. No skill approval on it.
- **No approve-all**: removed from Approve the skills and from a class's home assessments; the build fails for a new one.

## Chosen by default (nobody was asked)

- The brief says the staff table "already maps people to subjects". It did not (the Staff page said so: "Subject is not
  kept anywhere yet"). Subjects now sit in the same staff row beside the classes (config JSON, no DDL); none named is every subject.
- The count on What needs doing is red and amber rows (what a person must do); green rows ("when ready") are said apart.
- "Teaching now" is a topic with a skill in this week's `week_declaration`; "Next" is the first not-taught topic of its
  subject in `topic.ord`; no declaration, no "Teaching now".
- Topic flow, derived from the papers: skills ready (every skill of the topic approved); baseline (the class's first
  `assessment`); home assessments (`focus`: how many, how many children more than once); practice (`practice` papers
  made after the class was taught the topic). The data cannot tell which child went back to which earlier topic (a paper has a topic, not
  a reason), nor a baseline given on paper outside the system.
- Class result: the colour (red/amber/green) most of the topic's skill states hold; the worse on a tie. No new threshold.
- "What the system now knows" (five lines) and "Is the queue shrinking?" stay on What needs doing, folded/below the table.
- Per-skill "taught" switches are gone from Teaching (the teacher teaches a topic); `say_taught` still takes a skill.
- Two `/papers` files still have an approve-all button (`ux.approveAll` in `workflows.json`): another session owns them.

## Verified

(filled in below as each command is run)

## Handoff

- gstack could not be installed (the permission layer refused the clone-and-setup command, as last time): /design-review,
  /qa and /review did not run; Playwright and the Superpowers skills did instead.
- When ASM's `/papers` body lands, its two approve-all buttons should go and `ux.approveAll` should empty.
