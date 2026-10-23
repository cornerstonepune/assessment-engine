# ui-night-1-pages: each page moved onto the blocks, one PR each, stacked in order

Nimish's night orders, 22 Oct 2026. The design system is PR #290 (`docs/notes/ui-night-1-audit.md` has the audit). Each
section below is one stacked PR. Desktop (1440 px) first; screenshots before and after are in the PR.

## Taught this week (`/taught`) — goals/uxn2-taught-this-week.yaml

**Verified**
- Failing first: `u52-taught-this-week.spec.ts` (page does not exist).
- `bin/engine`-side: `test_ux_rules.py`, `test_layout.py`, `test_ratchet.py` → 21 passed (no database).
- Browser, on a `bin/testdb fresh` copy of this branch: `u52`, `u51`, `u30`, `u31`, `u40`, `u13`, `u17`, `u23`, `u46`, `u50`,
  `s2`, `u15`, `u18` → all pass. `u13`, `u17`, `u30`, `u31` read the topics at `/taught` now (they read `/?taught=1`):
  the words, the switches and who may say them are unchanged, only the address. `u31`'s topic list is read from the
  Assessments filter row's Topic dropdown (the tags were removed in #290).
- Words changed on purpose: Curriculum's top no longer holds the topics; a link "Taught this week →" does.

**Handoff**: the page's panels are folds of switches (held by u30/u31/u40). A table of every class and topic, with a
filter row, is its own slice. Schema follow-up: none.

## The menu (`components/shell.tsx`, `nav.tsx`) — goals/uxn3-the-menu.yaml

**Verified**
- Failing first: `u53-the-menu.spec.ts` (the menu had four tabs).
- Menu in the order of the week: Today · Taught this week · Papers to approve · Assessments · Upload papers · Check answers ·
  Class results; then, under "Setup": Curriculum · Question bank. Current page marked; only Today has a count; no subject named.
- Renamed on purpose, so the menu and the page say the same words: Marking → **Upload papers**; Check the answers →
  **Check answers** (back link "← Upload papers"); Children → **Class results**; Class papers to approve (the page) →
  **Papers to approve** (Today's own section keeps its name). The Question bank pages say "Question bank" above their title.
- Specs changed only for those words and for the menu's new items: `u1`, `u2`, `u3`, `u9`, `u15`, `u17`, `u50`, `screens`,
  `e2e`, `s1`, `s4`, `s42`, `u51`; `s1` lists `/taught` and `/papers/approve` among the pages the menu may pre-load.
  `u51`'s empty-column rule skips a paged table (its columns stay the same on every page).
- Phone: the row of nine tabs scrolls sideways (must not break); the top bar's search no longer pushes the page wider
  (a width transition measured mid-resize was the cause; removed).

## Papers to approve (`/papers/approve`) — goals/uxn4-papers-to-approve.yaml

**Verified**
- Failing first: `u37` (the table's new head, its order and the status chips) and `u24` (no class-and-week tags) were changed
  to the new page and failed on the old one.
- One table (`PackTable`): roll, child, level, why, paper, status chip, change level. A child with no paper and a spare copy are
  rows of it (red "no paper", amber "to approve", green "approved"), what needs the educator first. Filter row: class, week,
  kind, status. The pack's approval is the one main action, at the top; next step "Assessments".
- Off `ux.frozen`: `/papers/approve`. New state `noPaper` in `StatusChip`.
- Specs changed only for the new shape: `u37`, `u24`, `s7` (spares and the plan read across the table's pages).
- Phone: the change-level form opens full width (`u43` found it off-screen otherwise).

**Handoff**: the active-filter chips show the class, week and kind that the page picked by default; they can be removed but
the page then picks the first again.
