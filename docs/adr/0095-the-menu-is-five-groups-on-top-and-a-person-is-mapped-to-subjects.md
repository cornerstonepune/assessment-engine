# 0095 — The menu is five groups on the top bar, and a person is mapped to subjects

Goal: goals/nav_teacher_scope_and_todo.yaml

Nimish, 24 Oct 2026, looking at the live site after the UI wave: the menu was ten items down the left; Class and Subject
boxes sat on every page for everyone; Today was paragraphs and one button that approved everything below it.

## Decided

- **Menu.** One slim bar: the mark, five groups (What needs doing, Teaching, Assessments, Results, Setup), the search, and a
  three-line button that opens every group with its pages. A group's other pages are tabs under the bar. The map is
  `apps/web/lib/menu.ts`; no page's address changed.
- **Scope.** The staff row (`config.app.staff`) holds `classes` and now `subjects`. A person mapped to one class and one
  subject sees those and is offered no choice; a person on every class or on two or more subjects gets one "Viewing" control.
  A view, never a permission (`lib/access.ts` is unchanged). No subject named is every subject.
- **No approve-all.** An approval is a row's own action on its own item. `tests/u62` fails the build for a page with a button
  over every row; two pages of `/papers` (another session's) are listed in `workflows.json` `ux.approveAll` and only leave.
- **Teaching is topic-level.** Its flow is derived from the papers on record (`lib/topic-flow.ts`); skill approval lives in Setup.

## Rejected

- *Adding a `staff_subject` table.* The staff row already holds a person's classes; subjects beside them need no migration,
  and the Staff page edits both. A table is the answer when a person's subjects differ by class.
- *Keeping per-skill "taught" switches on Teaching.* The teacher teaches a topic; a skill is approved in Setup. The engine's
  `say_taught` still takes a skill; no screen offers it now.
