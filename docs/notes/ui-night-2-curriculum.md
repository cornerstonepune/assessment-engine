# ui-night-2-curriculum: Curriculum is one table of skills

Nimish, 2026-10-22: "the tags of subject names and all are never aligned, like on the curriculum page ... Can we use tables
more for easier viewing, and use icons or red, amber, green ... Use filters wherever possible." Goal:
`goals/uxn2-curriculum-table.yaml`. Slice CUR of UI part 2, stacked on `claude/ui-night-1-design-system` (UI part 1's
DataTable, FilterBar, StatusChip, top bar). Web only, no migration, no new table.

## Verified

- **Failing first:** the audit (PR #289, `docs/notes/ui-night-2-audit.md`) walked the old page at 1440 px: four closed "Grade n"
  bars, an "Open everything" button, no filter, no status chip, no column per grade, subject, topic. The new spec
  `tests/uxn2-curriculum-table.spec.ts` asserts the table named "The curriculum" with the six columns, a filter row and a
  search, so it cannot pass on that page.
- **The page:** `/` is a `PageShell` page: one table of skills (Grade, Subject, Topic, Skill, Levels, Status), a `FilterBar`
  (grade, topic, status with counts, a search), ten rows to a page, the skills waiting for approval first. The one action
  is "Approve N skills" (or "Open the question bank"); the next step is "Make an assessment". The tree with the bank's
  counts is behind "Question bank details" (`/?details=1`), as rule 8 asks; it moved to `components/curriculum-counts.tsx`.
- **Status:** one chip from three new states in `StatusChip` (`approved` green, `toApprove` amber, `notTaught` grey); nothing
  in the blocks names a subject (the subject is a column read from the data).
- **Off `ux.frozen`:** `/` is taken off the list in `workflows.json`.
- **Found and fixed in part 1's blocks (small commits, said in the PR):**
  1. `DataTable` drew its table with the class `fixed`, which Tailwind turns into `position: fixed`: the table took no
     room and drew over whatever came under it (the "Taught in each class" panel on this page; it would do the same
     under any page's table). The class is now `fixed-cols`.
  2. The top bar did not wrap: on a phone the 240 px search pushed the page sideways (`u5-curriculum` phone test).
     It wraps now.
- 3. The filter row's and the top bar's search drew its icon over the placeholder (the field's own padding won over `pl-9`): `!pl-9`.
  The phone search is 96 px (150 px focused) and 240 px from a tablet up, so nothing pushes a phone sideways.
- **Specs moved with the page** (the tree is no longer the first view): `s2-skill-map` (skills read page by page),
  `u50-declutter` (the Curriculum test, and its promise in `goals/ux10-declutter.yaml`), `u40`, `u46` (read the topic
  row's action on the details tree, `/?details=1`).
- `bin/check` → 31 passed. `npx tsc --noEmit` and `eslint` clean.

## Not changed, said plainly

- Versions of the curriculum come from the core track (C3); nothing here invents them.
- Failing on part 1's own branch before this slice, unchanged by it: `u16-assessments` (stage links),
  `u22-assessments-readable` (week table heads), `u51-ux-rules` ("the top bar: Class and Subject ... "),
  `e2e` "a count on the skill map opens exactly those questions", `u33-one-count` "the class papers Today counts".
  Same two or three Today/class-list failures the earlier notes record on a used copy.

## Handoff

- Next in the stack: Staff page (who teaches which class, the class part; subject is a schema follow-up), then Children,
  Question bank and Library, Approvals, School; English polish on #284's branch once it is green.
