# Five steps — the live website, the skill map, the worksheets, the queue, the bank explained

> For agentic workers: executed task by task in this session; each step ends only when
> `bin/engine goal <its goal>` is green, including its live-link criterion.

**Goal:** the five steps in `BUILD-ORDER.md` ("Now: five steps"), each proven by its goal file in
`goals/s1…s5-*.yaml`.

**Architecture:** no new service and no new language. The engine gains three small command groups
(`engine live`, `engine library`, `engine spec outcomes`) and two routes (`GET /worksheet/{code}.pdf`,
the re-read driver `engine read again`); the website gains a loading and an error screen, a rebuilt
Skill Map and skill page, a worksheet library, a validation queue, and three sentences on the bank.
One migration (library worksheets on `sheet_template`). Tests move to a local copy of the database.

**Tech stack:** Python 3.12 engine (FastAPI, psycopg, typer, pytest), Next 16 app (server
components, postgres.js, Playwright), Supabase Postgres 17, Vercel, the Lightsail engine server.

---

## Step 1 — the site answers (`goals/s1-site-answers.yaml`)

Files:
- Modify `apps/web/lib/db.ts` — `max_pipeline: 0`; `max: SERVERLESS ? 4 : 3` (ADR 0024).
- Create `apps/web/scripts/check-pooler.ts` — imports `../lib/db.ts` with `VERCEL=1` and the 6543
  address, fires eight `select n` at once, prints `8 of 8 answered` or exits 1 after 15 s.
- Create `apps/web/lib/deadline.ts` — `deadline(promise, ms = 8000)` rejects with `DatabaseSlow`.
- Modify `apps/web/lib/auth.ts` — `currentStaff` returns null only for a missing or bad cookie; a
  failed staff lookup throws (it used to send the person to the login page).
- Create `apps/web/app/(app)/loading.tsx` (skeleton) and `apps/web/app/(app)/error.tsx` (words and
  a Try again button).
- Every page's top-level `Promise.all` wrapped in `deadline(...)`; `lib/engine.ts` fetches carry
  `AbortSignal.timeout(15_000)`.
- Table links `prefetch={false}` (Skill Map, bank grid and list, worksheets, capture list, growth).
- Create `packages/engine/tests/conftest.py` — `DATABASE_URL = TEST_DATABASE_URL` before any test
  connects; refuse a non-local address. Create `tests/test_test_database.py`.
- `engine goal` scenarios run on `TEST_DATABASE_URL`.
- Modify `apps/web/playwright.config.ts` — production build in `.next-test` on port 3100 and an
  engine on 8932, both on the copy; a signed-in cookie minted for a test staff member in the copy.
- Create `apps/web/tests/s1-site-answers.spec.ts`:
  - a click on Question bank shows the loading screen within a second while `item` is locked;
  - with `item` locked, the page says the database did not answer, within 12 s;
  - with `config` locked, a page says so rather than showing the sign-in page;
  - opening the Skill Map makes at most six background page requests.
- Create `packages/engine/engine/live.py` + `engine live check [--since] [--page …]` — Vercel
  production logs (timeouts, 5xx, pages seen) and Supabase database logs (statement timeouts,
  slowest checkpoint).
- Ship: PR → checks green → merge → Vercel production; `deploy/go-live.sh` when the engine changed.
- Live gate: a person signs in once in the browser pane; every menu page and link clicked; `engine
  live check --since 60m` clean.

## Step 2 — the skill map as outcomes (`goals/s2-skill-map-outcomes.yaml`)

- `supabase/seed/skill_sets.json` and the 17 live rows: `learning_objective` rewritten — a verb
  first, one sentence, 8–30 words, the school's words, no codes. Applied as one update of the 17
  rows (the trigger versions each and withdraws its ratification); recorded in `STATE.md`.
- `engine spec outcomes` (in `engine/spec.py`) — the format check over the live rows.
- `/` rebuilt: skills grouped by grade band, each led by its outcome (link to its page), per level
  the worksheet and question counts, approval status; banner linking to `/skill-sets/approve` when
  any await approval; the registry panel removed.
- `/skill-sets/[code]` rebuilt as a read page: outcome, four level cards (the level's `words` and a
  real question from the bank drawn with `components/question.tsx`), kinds with an example each, the
  mistakes with their examples (top six, the rest folded), worksheets (step 3), Edit and Approve.
- `/skill-sets/[code]/edit` — name, outcome and the four level sentences only.
- `/skill-sets/approve` — the 17 as written, one button approving all in the person's name.
- `apps/web/tests/s2-skill-map.spec.ts` — every link on `/` opens; 17 skills in 5 grade groups;
  every skill page has four level cards with a sentence and a drawn question; editing withdraws the
  approval and approving restores it (on the copy).

## Step 3 — the worksheet library (`goals/s3-worksheet-library.yaml`)

- Migration `supabase/migrations/20260926090000_library_worksheets.sql`: `sheet_template.code`
  (unique per tenant), `retired_at`, `source` allows `library`, `week` nullable only for `library`.
- `packages/engine/engine/library.py`: `plan(unit_rows, per_sheet)` (pure — the deal), `build(conn,
  dry_run)`, `check(conn)`, `pdf(conn, code)`.
- CLI `engine library build [--dry-run]`, `engine library check`.
- Route `GET /worksheet/{code}.pdf` (`engine/api/routes/week.py` neighbour: `library.py` route file).
- Tests: `tests/test_library.py` (pure deal: 216 → 18 disjoint; 145 → 13; 24 → 10, each question 5
  times; kinds ±1; grouped print order; idempotent build; retire → replacement; printed never
  changes), `tests/api/test_library_routes.py` (PDF bytes, page count, 404 for an unknown code).
- Web: `/worksheets` — the library grid (skill × level counts) and a filtered list, then this week's
  papers; `/worksheets/[code]` — a library worksheet: facts, the 12 questions drawn, the answers, a
  Print link (`/api/worksheet/[code]` → engine PDF); the skill page's worksheet section with a level
  filter; the question page's "On worksheets" list.
- `apps/web/tests/s3-worksheets.spec.ts`.
- Build on live: `bin/engine library build`, then `bin/engine library check`, then `bin/testdb`.
- Deploy the engine (`deploy/go-live.sh`) for the PDF route.

## Step 4 — the validation queue (`goals/s4-validation-queue.yaml`)

- `engine read again` (in `engine/cli_read.py`, driver rebuilt from `capture` rows): re-reads every
  live capture no person has signed off or corrected (`legacy.worked_on`), keeps guesses, and prints
  every settled answer whose value changed. `tests/test_read_again.py` with a stand-in reader.
- Run it on live; record before/after `engine read waiting` and `engine read eval`.
- Web `/capture/check`: one waiting answer at a time in paper order — crop, question, guess, reason
  in words; Confirm (the guess), Save (typed), Right / Wrong / Blank for a judgement; one spot-check
  per paper; progress "n of N"; reached from Capture & Mark and the menu. Actions reuse
  `correctRead` / `judgeRead` with a return to the queue.
- Capture list: a sheet's score once nothing waits.
- `apps/web/tests/s4-validation-queue.spec.ts`.

## Step 5 — the bank explained (`goals/s5-question-bank-explained.yaml`)

- `/library`: three sentences at the top; each question row shows its skill (outcome), level, kind
  and worksheet codes as links.
- `apps/web/tests/s5-question-bank.spec.ts`.

## After each step

`STATE.md` gets the goal command and its output; `HANDOFF.md` names the next step; a PR per step;
the live gate before the next step starts.
