# Web app — the shell and the screens W1 already has data for

**Goal:** a staff member signs in, sees the six sections from the approved mockup, and can do the
three things the engine already supports: read the skill map with its coverage, edit and ratify a
skill-set spec, and browse or flag items in the bank. Sections whose data does not exist yet say
so plainly and name the workflow that produces it.

**Architecture:** Next.js (app router, server components by default), one `db.ts` reading
Postgres directly over `DATABASE_URL` from the server (no browser ever holds a key), Supabase
Auth magic link for identity, a staff allowlist in a `config` row, server actions for the two
writes (skill-set edit, item flag). Brand from the approved mockup (`design-system/PRINCIPLES.md`),
which overrides the Atlas house language for this product and says why.

**Not a mockup:** every number on every screen is a row. No sample data. A section without rows
shows what it will show and which workflow fills it.

## Screens

| Route | Section (nav) | Shows now | Actions now |
|---|---|---|---|
| `/` | Skill Map | NUM skills with their rungs; per skill set, how many active items exist at each difficulty; whether the set is draft or ratified | open a skill set |
| `/skill-sets/[code]` | Skill Map | the spec as Neha and Achal author it: name, objective, philosophy lines, formats, misconceptions, and the four difficulty bands (words + check) | save; ratify (sets `status`, `ratified_by`) |
| `/library` | Assessments | the bank: filter by skill set, difficulty, format, status; each item's equation or stem, answer, distractors, tags, times used | flag (retires by trigger; actor from the session) |
| `/worksheets` | Worksheets | the week's plan in words; no prescriptions exist until W2 | none |
| `/capture` | Capture & Mark | what the confirm queue will hold; no captures until W3 | none |
| `/growth` | Child Growth | what a child's map will show; no evidence until N3 | none |
| `/home` | Home Assignments | what the home sheet and note will show; nothing until W4 | none |
| `/login` | — | email field, magic link | sign in |

## Files

| File | Responsibility |
|---|---|
| `apps/web/design-system/PRINCIPLES.md` | why this product uses the mockup's brand, not Atlas |
| `apps/web/app/globals.css` | brand tokens as CSS variables; Tailwind theme |
| `apps/web/app/layout.tsx` | fonts, sidebar, topbar slot |
| `apps/web/components/shell.tsx` | sidebar nav, page header (stage, title, sub, chalkline), panel, pill, chip, table |
| `apps/web/lib/db.ts` | the only Postgres connection (`postgres` package, server-only) |
| `apps/web/lib/auth.ts` | session → staff record, or redirect to `/login`; allowlist from `config.app.staff` |
| `apps/web/middleware.ts` | refresh the Supabase session cookie |
| `apps/web/app/(app)/…/page.tsx` | one folder per route above |
| `apps/web/app/(app)/skill-sets/[code]/actions.ts`, `library/actions.ts` | the two server actions |
| `supabase/seed/config.json` | `app.staff` row |
| `apps/web/tests/screens.spec.ts` | Playwright: every route renders at 1440 and 400 px, one screenshot each |

## Order

1. Scaffold, tokens, fonts, shell with the six nav entries. Every route renders its header.
2. `db.ts` + Skill Map with real counts.
3. Skill-set page with save and ratify.
4. Library with filters and flag.
5. Auth: magic link, allowlist, middleware. Dev bypass only when `NODE_ENV=development` and
   `AUTH_DEV_BYPASS=1`, printed as a banner.
6. Playwright screenshots; STATE, HANDOFF, commit.

## Success criteria — each is a command

1. `cd apps/web && npm run build` → no type errors, no lint errors.
2. `npx playwright test` → 8 routes × 2 widths pass, screenshots in `apps/web/test-results/`.
3. Skill Map shows the four seeded skill sets with the real active-item count per difficulty
   (`SUB.2D.EXCH Hard` matches `select count(*) from item where …`).
4. Editing a difficulty band's words on `/skill-sets/SUB.2D.EXCH` and saving changes the row's
   `difficulty` JSON and `updated_at`; `engine load` afterwards does not overwrite `status`.
5. Flagging an item on `/library` inserts an `item_feedback` row with the signed-in email as
   actor and the item shows `retired` on reload.
6. With no session, every route redirects to `/login`; an email not in `app.staff` is refused.

## Not in this chunk

The Generate form (needs the HTTP engine and W2), previews rendered as paper (the Python
renderer owns that), Capture/Growth/Home beyond their honest empty states.
