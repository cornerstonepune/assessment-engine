# nav3-what-needs-doing: no filter in the top bar, What needs doing as groups, Teaching gone

Nimish, 26 Oct 2026, on the live site (his words are in `goals/nav3_what_needs_doing.yaml`).
Goal: `bin/engine done nav3_what_needs_doing`. Website only: no migration, no engine change. W3, no gate moved.

## What was built

- **Top bar**: the Viewing control (Class and Subject) is gone, with its `choose` action, its two cookies and `isBroad`/`subjectNow`/
  `viewSubject`/`viewingWords`. A person sees what their staff row names (classes, subjects); each page narrows with its own `FilterBar`.
- **What needs doing** (`/today`): nine kinds of work in the order the week runs (`TODO_GROUPS`, `lib/todo.ts`): skills, questions,
  topics to mark taught, assessments to make, class papers, scans to read again, answers to check, home assessments, parent reports.
  One line each: heading (opens its page), count, red/amber/green, next action; folded until opened into its own table. A topic is
  marked taught in its own row (class chosen in the row), then the page comes back.
- **Teaching** is out of the menu (four top-level items now); `/taught` redirects to `/today` (`next.config.ts`).

## Parked

- **Is the queue shrinking?** (week-by-week answers read, settled by the engine, checked by a person; how near the reader is to
  trust on each kind). Removed from What needs doing. Kept, unused: `app/(app)/today/shrinking.tsx`, `queueByWeek` and `trustNow`
  in `lib/queries-today.ts`. It belongs on Results (class results) or Setup (the reader's trust, by kind); neither has it yet.
- **Topic flow** (skills ready, baseline, home papers, practice per class) and the **class-result colour** of a topic: no page owns
  them now. `teaching()` (`lib/queries-teaching.ts`) and `topicFlow()` (`lib/topic-flow.ts`) are kept and tested; nothing draws them.

## Chosen by default (nobody was asked)

- A group's line says how many rows it has (papers, classes, topics), not how many answers or questions inside them.
- "Answers to check" holds both checking a paper and signing it off: one piece of work, two actions.
- "Papers to read again" is the scans nothing came back from; the system has no list of papers not yet uploaded, so none is shown.
- The main button still says "Start with" the most urgent row (red first); the list itself follows the week's order.
- A Class filter and (for a person with several subjects) a Subject filter sit on the page; the menu's count is not narrowed by them.

## Verified

(filled in as each command is run)

## Handoff

(filled in at the end)
