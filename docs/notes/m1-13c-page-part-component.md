# m1-13c: one component draws a page part (W1, gate N1, screens only)

## Verified
- `cd apps/web && npx playwright test tests/m1-13c-page-part.spec.ts tests/m1-13-curriculum-fill.spec.ts tests/u51-ux-rules.spec.ts tests/u53-the-menu.spec.ts --reporter=line` → 23 passed. The component's 3 tests were written first and seen failing (the files absent: 3 failed).
- `bin/check` → 34 passed. `cd packages/engine && uv run pytest -q tests/test_grades.py tests/test_ux_rules.py tests/test_web_gate.py tests/test_layout.py tests/test_contract.py` → 30 passed. `cd apps/web && npx tsc --noEmit` and `npx eslint --max-warnings 0` on the changed files → no output (clean).
- A fourth test draws a real page and reads the computed styles (a card with its edge, a slip's keyword in the state colour), because the first three read source text.

## What changed (no behaviour, no migration, no engine change)
- `lib/page-part.ts`: the shapes (`PagePart`, `Slip`, `PartKey`) and the school's words for the eight parts (`PART_WORDS`); pure.
- `components/page-part/part.tsx` + `page-part.css`: `PartView`, `Words`, `Origin`. The tokens only; icons from `lib/icons`.
- `app/(app)/curriculum/parts.tsx` draws its parts with `PartView`, keeping only its editor and its Keep / Edit / Send back.

## For a screen that uses it (the educator's activity page)
```tsx
import { PartView } from "@/components/page-part/part";
import type { PagePart } from "@/lib/page-part";
<PartView part={p} />                         // read-only: heading (an h2), whose words, the words
<PartView part={p} actions={<form …/>} />     // its own buttons, below the words
<PartView part={p} editor={<form …/>} />      // an editor in place of the words (actions are then not shown)
```
`PartView` reads and asks nothing: no session, no engine call, no gate. The screen decides who may do what and passes the
buttons in (or none). `part` is one element of `parts` in `POST /curriculum/page/read` (docs/notes/m1-12b-apply-and-edit.md).
It carries `data-card`, `data-source` for tests. Its CSS needs the school's tokens (inside `SchoolShell` they are loaded).

## Handoff
- Next: the curriculum screens onto `SchoolShell` and the educator gate (branch m1-13b, held until this is on main).
