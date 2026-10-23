# UX rules for the educator's site

Approved by Nimish, 2026-10-22. Held by tests (below); the pages that still break them are listed in `workflows.json`
under `ux.frozen`, and the list only shrinks.

## Desktop first (Nimish, 2026-10-22, night orders)

Educators use the site on a desktop. Every screen is designed, tested and screenshotted at 1440 px. A phone must not
break (no error, no lost action) but no screen is held for it, and rule 7's phone line is no longer a gate. The one
exception is KG observation (S9), which is done on a phone.

## The eight rules, and three more for the desktop

1. **One purpose, one main action.** The title says what the page is for; one main action; the page ends on a link to
   the next step. No dead ends.
2. **One table style.** The same columns, date and number formats, status chips and words everywhere.
3. **No long tables.** At most 10 rows shown (`TABLE_ROW_LIMIT`). More are grouped by week or class, or paged, with
   what needs the educator first.
4. **No empty noise.** No column of zeros or dashes, no empty chip, no line under the title over 140 characters
   (`PURPOSE_MAX`).
5. **One count, one meaning.** Computed once, the same on every page and in the menu. Only Today has a red count.
6. **The school's words.** Educator, regroup, Easy/Medium/Hard/Advance. No taxonomy, rung or kind on an educator's screen.
7. **Phone and desktop.** Desktop first (above). A table becomes a list on a phone; it must not break there.
8. **Setup out of the way.** Statistics, question counts, old scans and reader statistics sit behind a "details" link.
9. **A list is a table, and a table has its filter row.** Rows and aligned columns: subject, class, grade, status and the
   like are columns, never tags floating in a line. Text is left, numbers right, a status centred, each column the same
   width on every page of its kind; the head stays at the top and a row lights under the pointer. Six rows or more have a
   `FilterBar` above them, in the same place on every page: dropdowns (class, subject, grade, status, week, as fit), a
   compact search, the filters that are on shown beside them with a × each, and one click to clear them all.
10. **A status is an icon, a word and a colour.** Never colour alone. One chip (`StatusChip`), one map of the school's
   states to green (done, right), amber (waiting on someone or something) and red (needs the educator now), and a quiet
   grey for a state with nothing to do. Red is rare. A state is added to `STATES` before a page uses it.
11. **The top bar is for using.** Class and Subject are full-size controls, at least 40 px tall with 15 px text, showing
   the current choice. The student search is a compact field of about 240 px with a search icon, growing when focused.
   Nothing in a shared block or the menu names a subject: every subject inherits them.

## The educator's week, and its pages

| Day | Step | Page |
|---|---|---|
| Wednesday | declare what was taught | Today; Taught this week |
| Thursday, Friday | approve | Papers to approve |
| Friday | give | Print and give |
| Monday | act | Upload papers; Check answers (`/capture/check`); Class results; A child |
| Setup | | Curriculum; Question bank; School |

## The blocks (`apps/web/components/`)

| Block | Use it for |
|---|---|
| `PageShell` | Every page. Props: `stage`, `title`, `purpose` (one line, 140 characters at most), `action` (the one main action), `next` (the next-step link), `details` (optional link to setup and numbers). `action` and `next` are required, so a page cannot leave them out. |
| `DataTable` | Every table. Props: `columns` (with a `value` for each cell, which is what empty-column hiding reads), `rows` (needs-you first), `rowKey`, and `more`: either `{ by, href? }` to group, or `{ page, href }` to page. `more` is required, so a table that can pass 10 rows always has a way to the rest. A column says how it aligns (`num` right, `status` centred, else left) and may fix its `width`. `extras` adds a row's data attributes and a full-width row under it (an assessment opened to its copies). On a phone it is a list of labelled cards. |
| `StatusChip` | A state in a row or a heading: icon, word, green, amber or red. The states, words and tones are in `STATES`; add one there first. |
| `FilterBar` | The filter row over a table: `filters` (a dropdown each: name, label, value, "all" words, options), `search`, `keep` (what the page holds while filtering). A GET form: the filters are in the address. |
| `EmptyState` | Nothing to show. On a `PageShell` page the shell supplies the next step. |
| `Count` | A number of things waiting. Give it the same `of` and value wherever it appears; the menu's badge carries the same `data-count`. |

Rules and constants: `apps/web/lib/ux-rules.ts`. The first page on the blocks is `/capture/check`; copy it.

## How the build holds the rules

- `packages/engine/tests/test_ux_rules.py` (in `bin/check`, no database): a page not on the list must be built on
  `PageShell`, have no hand-built `<table>`, and no `sub=`/`purpose=` over 140 characters; a page on the list must
  still break exactly what it lists.
- The same test holds rules 9 to 11: a page with a hand-drawn `chip` is a tag list (`taglist`), a table with no `FilterBar`
  has `filter`, a `<Pill>` or `<MarkPill>` drawn by hand is a status with no icon (`status`); `StatusChip` cannot draw a
  state without its icon; the top bar's sizes are read from `lib/ux-rules.ts` (`TOP_BAR_MIN_PX`, `TOP_BAR_TEXT_PX`,
  `SEARCH_PX`). A rule written down for the first time lists the pages that break it once (`ux.rules`); after that it
  ratchets like the others.
- `engine ratchet` (CI): nothing joins `ux.frozen`, no rule comes back to a page that kept it.
- `apps/web/tests/u51-ux-rules.spec.ts` (browser): each page as it renders: a table over 10 rows, a column of zeros or
  dashes, a count that differs from the menu's, no main action or next step, a line over 140 characters, a table of six rows with
  no filter row, a status with no icon; and the top bar's sizes. A page not on the list must keep all of them.

## Taking a page off the list

1. Build the page on `PageShell`, and its tables on `DataTable`.
2. Delete its entry from `ux.frozen` in `workflows.json` (the test fails until you do, and fails if you do not).
3. Run `bin/check` and `cd apps/web && npx playwright test tests/u51-ux-rules.spec.ts`.
4. Note it in the branch's `docs/notes/<goal>.md`.

Not yet held by a test: the menu shows a red count on every tab (rule 5 allows red on Today alone); rules 6 and 8 are
reviewed by eye. The first waits for the slice that moves Today.
