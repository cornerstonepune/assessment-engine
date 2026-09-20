# STATE — what is verified true

Each line: a claim, the command that proves it, its last output. No claim without a check.

## Design

- Spec approved in shape by Nimish (approach A); written as `SPEC.md`; awaiting his read-through.
- ADRs 0001–0003 record the stack, the skill model, and the n8n boundary.

## Inputs verified

- Registry: `window.CSMAP` from the Skill Map Review artifact — 244 skills, 849 milestones,
  14 domains, NUM = 37 skills. All seven skill ids the ladder maps to exist
  (`NUM.OPS.01/.02/.05`, `NUM.PRB.02/.03`, `NUM.PV.03`, `NUM.MEAS.04`).
  Check: `python3 -c` parse of `data.js` → counts above.
- Prototype: `~/Downloads/assessment-engine-prototype/assess/` — 8 modules; synthetic roundtrip
  report: cell geometry agreement 1.0 on 4/4 sheets, QR decoded 12/12 pages; status agreement
  0.40–0.70 with the Tesseract stub (not for handwriting, by its own docstring).
- Existing scans: 13 `ACE Scanner_20260916(N).pdf` — none carry fiducials or a QR, none have a
  text layer. Check: prototype `find_fiducials` + `cv2.QRCodeDetector` on page 1 of each → 0/13.
  Therefore every existing assessment goes through legacy import. Real Phase 1 input is
  whatever Nimish uploads to `~/cornerstone/assessments/` (layout in its README); the Downloads
  scans were evidence only.
- Team documents incorporated: `Addition_Subtraction_Assessment_Skill_Taxonomy.pdf` (13 pp;
  §12 tag matrix, §13 progression) and `Adaptive_Subtraction_Learning_Engine_…Spec.docx`
  (M001–M010 conceptual misconceptions).

## Handwriting reading — first real measurement (2026-09-17)

One real Grade 3 paper (`ACE Scanner_20260916(2).pdf` p1, Sep Week 1), name band masked before
sending, `legacy_extract` prompt v1, `gemini-3.5-flash`, 1,237 in / 695 out tokens.

Read correctly, checked against the page: Q1 a=53 b=612 c=1250 d=36 (all four arithmetically
consistent); Q2 balance = 600; Q3 blank and circled, correctly reported as not attempted;
Q4 number line landing 78, answer 83; Q6 column 675+589 = 1264. It also caught the teacher's
circles on Q1 b/d, and on Q5 read the child's partition of 638 as 600+19+19 — a wrong method
reaching a right answer (1113), which is exactly the diagnostic signal the product exists to find.

**Status: promising signal, not a measurement.** One page, one child. The real figure comes from
the Phase 1 `gold` set against Aseem's own marking.

Three things this spike changed:
1. `legacy_extract` needs a `part` field — Q1's four lettered sub-answers arrived crammed into one
   string. Marking needs one row per response.
2. Teacher annotations are legible to the model. Useful for Channel B; Channel A must be told not
   to read a teacher's circle as the child's answer.
3. Free tier returns 503 and intermittent 404 under load. The adapter needs retry with backoff
   and an ordered model fallback list, not a single pinned id.

Model availability (checked live, `models.list`): flash line runs to `gemini-3.8-flash`;
`gemini-3.8-flash` was overloaded, `gemini-3.5-flash` served. `gemini-2.5-flash` — the brain's
2026-09-08 choice — is now three generations back. Never use the `gemini-flash-latest` alias:
a silent model change would invalidate every accuracy measurement taken against it.

## Phase 0 — schema

Two migrations applied to the hosted project `ruznbyngtfjsaymuylhm` (ap-south-1) with
`supabase db push --db-url "$DATABASE_URL"`: `20260917090000_ring_a.sql` (Ring A, the `pii`
schema, `internal.apply_conventions()`) and `20260917090100_ring_b.sql` (the three derived
tables). The full schema exists now, so Phases 1–4 add rows, never DDL. Every check below is
run after `cd ~/cornerstone/assessment-engine && set -a && . ./.env && set +a`.

- Both migrations are recorded as applied, and nothing else is.
  Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from supabase_migrations.schema_migrations order by version"` →
  ```
  20260917090000 ring_a
  20260917090100 ring_b
  ```

- 30 tables exist across `public` and `pii` — the 26 Ring A tables, `pii.child`, and the 3 Ring B
  tables. Check: `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii')"` → `30`

  The list, with `relrowsecurity` and `relforcerowsecurity`. Check:
  `psql "$DATABASE_URL" -c "select n.nspname as schema, c.relname as table, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') order by 1,2"` →
  ```
   schema |         table         | rls_enabled | rls_forced
  --------+-----------------------+-------------+------------
   pii    | child                 | t           | t
   public | access_log            | t           | t
   public | blueprint             | t           | t
   public | capture               | t           | t
   public | case_dimension        | t           | t
   public | child                 | t           | t
   public | child_skill_state     | t           | t
   public | class_card            | t           | t
   public | config                | t           | t
   public | coverage_target       | t           | t
   public | evidence_event        | t           | t
   public | flow_run              | t           | t
   public | gold                  | t           | t
   public | home_sheet            | t           | t
   public | item                  | t           | t
   public | item_result           | t           | t
   public | item_stat             | t           | t
   public | level_rule            | t           | t
   public | milestone             | t           | t
   public | misconception         | t           | t
   public | narrative_observation | t           | t
   public | parent_note           | t           | t
   public | prescription          | t           | t
   public | prompt                | t           | t
   public | rung                  | t           | t
   public | sheet_instance        | t           | t
   public | sheet_template        | t           | t
   public | skill                 | t           | t
   public | tenant                | t           | t
   public | threshold             | t           | t
  (30 rows)
  ```

- Not one table is missing RLS, and none is missing the forced flag — so the owning role is
  subject to the policies too. Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not (c.relrowsecurity and c.relforcerowsecurity)"` → `0`

- Every one of the 30 tables carries the `service_role_all` policy. Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not exists (select 1 from pg_policies p where p.schemaname=n.nspname and p.tablename=c.relname and p.policyname='service_role_all')"` → `0`

- `tenant` is the only table without a `tenant_id` — it is the tenant. Check:
  `psql "$DATABASE_URL" -Atc "select n.nspname||'.'||c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind='r' and n.nspname in ('public','pii') and not exists (select 1 from information_schema.columns k where k.table_schema=n.nspname and k.table_name=c.relname and k.column_name='tenant_id') order by 1"` →
  ```
  public.tenant
  ```

- `evidence_event` is append-only, enforced by a statement-level trigger, so it refuses the write
  even when no row matches. Check:
  `psql "$DATABASE_URL" -Atc "update evidence_event set correct = true where false"` and the same
  with `delete from evidence_event where false` →
  ```
  ERROR:  evidence_event is append-only: UPDATE is not allowed
  ERROR:  evidence_event is append-only: DELETE is not allowed
  ```

- No foreign key column is left without a covering index — the query returns every FK constraint
  whose columns are not the leading columns of some index, and returns none. Check:
  `psql "$DATABASE_URL" -Atc "select c.conrelid::regclass::text||' ('||c.conname||')' from pg_constraint c where c.contype='f' and c.connamespace in ('public'::regnamespace,'pii'::regnamespace) and not exists (select 1 from pg_index i where i.indrelid=c.conrelid and (string_to_array(i.indkey::text,' ')::smallint[])[1:array_length(c.conkey,1)] @> c.conkey) order by 1"` →
  (no rows)

- No column anywhere is `double precision` or `real`; every measured value is `numeric`
  (`threshold.value` and `flow_run.cost_inr` at `numeric(20,4)`, `p_correct` and
  `read_confidence` at `numeric(5,4)`). Check:
  `psql "$DATABASE_URL" -Atc "select table_schema||'.'||table_name||'.'||column_name||' '||data_type from information_schema.columns where table_schema in ('public','pii') and data_type in ('double precision','real') order by 1"` →
  (no rows)

- Names are reachable only through the logging accessor: `pii.read_child(child_id, actor)` writes
  `access_log` before returning, and `anon` / `authenticated` are revoked from the schema.
  Check: `psql "$DATABASE_URL" -Atc "select proname from pg_proc where pronamespace='pii'::regnamespace"` →
  ```
  read_child
  ```

- Only one prompt version per purpose can be active, enforced by a partial unique index. Check:
  `psql "$DATABASE_URL" -Atc "select indexdef from pg_indexes where tablename='prompt' and indexname='prompt_one_active_idx'"` →
  ```
  CREATE UNIQUE INDEX prompt_one_active_idx ON public.prompt USING btree (tenant_id, purpose) WHERE active
  ```

Empty by design, each with a comment at its definition saying so: `blueprint`, `threshold`,
`config`, `case_dimension`, `coverage_target` (first read by Phase 2), and every operational
table (`child`, `item`, `sheet_*`, `capture`, `item_result`, `evidence_event`, `gold`,
`home_sheet`, `parent_note`, the three Ring B tables). `tenant` and the registry, ladder,
misconception and prompt tables are filled by `engine load`.

## Phase 0 — seeds and loader (complete 2026-09-17)

`engine load --check` fills the hosted project from `supabase/seed/`, checks every code
resolves, then loads again and fails if any count moved.
Check: `cd packages/engine && uv run engine load --check` →
```
  tenant               1
  skill               37
  milestone          162
  rung                16
  level_rule          12
  misconception       27
  case_dimension      18
  coverage_target     46
  prompt               5
  threshold           10
  every code referenced resolves
  unchanged on a second run
```

Test suite: 53 tests, all passing, including the live loader tests against Supabase.
Check: `cd packages/engine && uv run pytest -q` → `53 passed`

Three misconceptions were seeded as `answer_lookup` — a promise that the engine can compute
the number the mistake produces — with no predictor behind them. `test_every_seeded_answer_lookup_code_has_a_predictor`
caught it. Now written: `align_left` (342 + 5 with the 5 under the 3 → 842, the error the
unequal-length blueprint slots exist to catch), `zero_dropped` (495 + 505 → 100), and
`carry_always_one`, which needed its own `MULTI_PREDICTORS` registry because it takes a list of
addends — two operands can never make a column total of 20, so the error is invisible until a
sheet asks for three. Verified live: `7489 + 8845 + 3539 = 19873`, a child always carrying 1
writes `19863`.

## The misconception vocabulary matches an expert's independent diagnosis (2026-09-17)

Aseem's written report on a real Grade 3 child names the error — "subtracts the smaller digit
from the larger digit in each column" — and gives the example `8500 − 3647 = 5147`. The report
was written by hand, months before this engine existed.

`M_SMALL_FROM_LARGE` given those operands returns **5147**. The six other subtraction predictors
return 4852, 4863, 4953, 4863, 5963 and 12147 — so the match is unambiguous, not a coincidence
of a crowded answer space.
Check: `cd packages/engine && uv run python -c "from engine.assess import misconceptions as M; print(M.predict('-', 8500, 3647))"`

This is the strongest evidence so far that marking by lookup produces the same diagnosis a good
teacher reaches, and it is why the five Grade 3 reports become the `gold` set for the whole
pipeline rather than only for digit reading.

Not covered: Aseem's second finding, `56 × 3 = 1518` (partial products written side by side), is
multiplication. Off the ladder, no predictor — the `M_MULT_CONCAT` the Kabir POC proposed.

## Prompt-driven item generation — first measurement (2026-09-17)

The bank generated the way the founder specified: the skill-set spec as plain text (topic,
objective, skill, Hard rule in words, philosophy lines, formats, the eleven seeded subtraction
misconceptions with descriptions), one prompt, no per-topic code; then every number checked by
code. Full reading in `research/2026-09-17-prompt-generation-spike.md`; decision in ADR 0005.
Check: `cd packages/engine && uv run python ../../research/spike_prompt_gen.py 20` →
```
model used: gemini-3.6-flash
model returned 20 items (asked 20)
answers correct:        17/20
constraint met:         20/20  (3-digit, no zero on top, exactly one exchange)
duplicate (a,b) pairs:  0
misconception claims:   89; with a code predictor: 89; matched predictor: 77
formats: {'column': 7, 'missing_number': 7, 'word_1step': 6}
```
The three rejected items were `582 − □ = 236`-shaped: the model wrote the shown difference into
both `b` and `answer`. Its distractors for that item (244, 246, 235, 928) equal the predictors'
output for 582 − 346, so the arithmetic was right on all twenty and the verifier caught the field
error. 77/77 distractors on the seventeen accepted items matched code. A 40-item request timed
out at 120 s on the free tier — batch at ~20. `gemini-3.5-flash` returned 503 then a spurious
404 on this run; the ordered fallback served.

**Status: one call, one topic, one difficulty.** Enough to choose the architecture, not a quality
measurement. The seventeen accepted items seed the `item_generate` eval set.

## W1 — the question bank as engine code (2026-09-17)

Plan: `docs/superpowers/plans/2026-09-17-w1-bank.md`. Design: ARCHITECTURE §7, ADR 0005.

- Migration `20260917120000_skill_set_and_feedback` applied and recorded (the `supabase db push`
  output shows a pg-delta certificate error from a Supabase helper, then finishes; the check is
  what counts). Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from supabase_migrations.schema_migrations order by version"` →
  ```
  20260917090000 ring_a
  20260917090100 ring_b
  20260917120000 skill_set_and_feedback
  ```
  `skill_set` and `item_feedback` exist; `item` has `skill_set_code` and `difficulty`. 32 tables.

- Seeds: four skill sets at Easy/Medium/Hard/Advance (drafts for Neha and Achal), two config
  rows (school philosophy, model fallback list), the `item_generate` prompt.
  Check: `cd packages/engine && uv run engine load --check` → the Phase 0 counts plus
  ```
  prompt               6
  config               2
  skill_set            4
  every code referenced resolves
  unchanged on a second run
  ```

- Tests: 98, including live bank tests that run inside a rolled-back transaction against the
  hosted project. Check: `cd packages/engine && uv run pytest -q` → `98 passed`.

- **The real fill, three runs, each of which taught something now in a test:**
  1. Died on the first batch: the model wrote U+2212 for minus and the schema's enum refused the
     reply. Now `verify.normalise` folds symbols; schema takes any single character.
  2. Eight successful calls, 162k tokens, **zero items stored**: every item carried a claim our
     predictor cannot check ("aligns from the left" on 243 − 27 gives a negative) and an
     off-by-one written +1 where the predictor says −1. Both were verifier strictness, not model
     error — the six candidates inspected by hand all had correct numbers. Now: unverifiable
     claims are dropped and the item survives; "plus-or-minus" codes accept either sign.
  3. `uv run engine bank fill SUB.2D.EXCH Hard --n 200` → 40 items in four batches, ten per
     format, then the free tier rate-limited every model. Check:
     `psql "$DATABASE_URL" -c "select fmt, count(*) from item where source='generated' and status='active' and skill_set_code='SUB.2D.EXCH' group by fmt"` →
     ```
     bare_sum       10
     column_grid    10
     missing_number 10
     word_1step     10
     ```
     A word problem from the bank: "Aarav saved 472 rupees for the mela and spent 38 rupees on
     rides, how many rupees does he have left?"

- Independent audit of everything stored. Check: `uv run engine bank recheck` → `0 mismatches`.

- A sheet from the bank, through the existing renderer unchanged.
  Check: `uv run engine bank sheet SUB.2D.EXCH Hard --n 12 --out data/bank` →
  `CS289D43  2 pages  12 responses  -> data/bank/CS289D43.pdf`. Looked at both pages: QR,
  fiducials, column grids, digit cells, working boxes, key JSON beside it.

- Free-tier numbers to plan around (`flow_run` rows): ~20k tokens and ~95 s per 20-item call;
  the limit closes after roughly four calls in a row; `gemini-2.5-flash` is retired for new
  users (404 with that message). The adapter now waits 5/10/20/40/60 s per model and 60 s on a
  429; a 200-item fill is a background job of ten to fifteen minutes.

- A fourth fill with the patient policy got **no call through in 886 s**: every attempt on all
  three models returned 503 "This model is currently experiencing high demand". That is
  Google's capacity for free-tier traffic at that hour, not our quota. Check: the `flow_run`
  row at 12:27:53 UTC, status `error`, 886 s.

- **The binding limit is 20 requests per day per model** on the free tier
  (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 20, read from the 429 body).
  Tokens are not the constraint; requests are. The adapter now skips a model whose daily quota
  is gone instead of waiting on it. The lever is more items per request, to be measured when
  the quota resets.

- `gemini-3.5-flash-lite` is not a usable fallback: one real call at n=20 returned 20 items and
  the verifier accepted **0** — every item had two exchanges where the rule asks one, and its
  distractor arithmetic was wrong. The verifier earned its keep; the model is out of the list.
  Turning thinking off (`thinkingBudget: 0`) is rejected with 400 on these models; the
  reasoning is what makes the exchange count hold, so it stays on.

- Fifth fill, with quota skipping: the two exhausted models were passed over at once, the third
  was tried through all five waits and returned 503 "high demand" every time; the run ended in
  226 s with one reason per model. Check: the `flow_run` row at 12:48:23 UTC. **The bank stands
  at 40 verified items until the daily quota resets** (midnight Pacific, about 12:30 IST).

- Not yet run: `engine eval item_generate` across all four sets × four bands — it needs sixteen
  calls the free tier will not grant in one sitting. The 40 stored items are the first eval seed.

## The web app — shell and the W1 screens (2026-09-18)

Plan: `docs/superpowers/plans/2026-09-18-web-shell-and-w1-screens.md`. Brand:
`apps/web/design-system/PRINCIPLES.md`, from the Cornerstone Brand Book Edition 02 (it overrides
the Atlas house language for this product, and says why). Screens published for review:
claude.ai/artifact/D1zoM7ZZX8nSfWswvH2mQR

- Builds clean, no type errors, eight routes.
  Check: `cd apps/web && npm run build` → `✓ Compiled successfully`, routes `/ /_not-found
  /capture /growth /home /library /login /skill-sets/[code] /worksheets`. No Proxy: the
  middleware existed only to refresh a Supabase session and went with it.

- Every screen renders its heading, scrolls sideways nowhere, and logs no console error, at
  1440 px and at 400 px. Check: `cd apps/web && AUTH_DEV_BYPASS=1 npx playwright test` →
  `16 passed (5.4s)`.

- The Skill Map shows the real per-difficulty counts: `SUB.2D.EXCH` reads 80 at Hard and 0
  elsewhere, matching `select count(*) from item where skill_set_code='SUB.2D.EXCH'`.

- **Editing a difficulty in the app writes to the database, through plain fields — no JSON.**
  Verified end to end in the browser: changed the Easy band's words and ticked a second exchange,
  pressed Save, then
  `psql "$DATABASE_URL" -Atc "select difficulty->'Easy' from skill_set where code='SUB.2D.EXCH'"` →
  ```
  {"check": {"op": "-", "digits": [2, 1], "regroups": [1, 2]}, "words": "… EDITED BY TEST."}
  ```
  and `updated_at` moved. The test edit was then restored to the seeded values.

- **Bug found and fixed by that test:** `engine load` used to upsert `skill_set`, so the next
  load would silently overwrite whatever Neha and Achal had authored in the app. The loader is
  now insert-only for that table, with `test_load_does_not_overwrite_a_skill_set_edited_in_the_app`
  as the regression. Engine suite: 101 passing.

- Sign-in is email and password against the staff allowlist in `config.app.staff`, which holds a
  `scrypt$salt$hash` per person; the session is an httpOnly cookie signed with `AUTH_SECRET`
  (HMAC-SHA256, 30 days). Every route in the app group is behind it and both server actions check
  again on their own. A development bypass exists, is refused outside development, and shows a
  "dev bypass" pill in the sidebar when on.
  Check: `cd apps/web && npm run test:gate` → `8 passed`, seven routes redirecting and a wrong
  password refused. `npm run test:screens` → `32 passed`.

  It replaced the magic link on 2026-09-18, after the live site returned `over_email_send_rate_limit`:
  Supabase's built-in mail sender allows two emails an hour, and there is no other sender on the
  project. Check: `curl -s -X POST "$SUPABASE_URL/auth/v1/otp" …` →
  `{"code":429,"error_code":"over_email_send_rate_limit"}`; and the project's auth config reads
  `rate_limit_email_sent = 2`, `smtp_host = None`.
  Check: `curl -s "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/config/auth" -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN"`.

- `SUPABASE_SERVICE_ROLE_KEY` in the repo `.env` does not authenticate — the project rejects it on
  both the auth admin API and PostgREST. Nothing in the engine uses it (data goes through
  `DATABASE_URL`), so it is dead rather than breaking, but it is wrong and should be re-copied or
  deleted. Check: `curl -s -o /dev/null -w "%{http_code}" "$SUPABASE_URL/rest/v1/config?select=key&limit=1" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"` → `401`.

- Not built: the Generate form (needs W2), paper previews (the Python renderer owns those), and
  Capture, Child Growth and Home Assignments beyond their honest empty states, which name the
  workflow that fills them and show the real table counts.

## W2 — the week's papers, and the dashboard tested end to end (2026-09-18)

Migration `20260918100000_prescription_difficulty` applied: a prescription now names a skill set
and a difficulty (the retired `level` stays, nullable), plus `item_exposure` so a child is never
shown the same question twice. Check: `psql "$DATABASE_URL" -Atc "select version||' '||name from
supabase_migrations.schema_migrations order by version"` → four rows ending
`20260918100000 prescription_difficulty`.

- **The real roster is loaded.** 16 children, names in `pii` only.
  Check: `uv run engine week roster ~/cornerstone/assessments/roster.json` → `added 16`.

- **The week is prescribed with a reason per child.**
  Check: `uv run engine week prescribe G3 T2W1 --set SUB.2D.EXCH` →
  ```
  1   G3  Medium   not enough of their own work yet, so this is the starting level for their grade
  …
  5   G4  Hard     not enough of their own work yet, so this is the starting level for their grade
  1 at Hard · 4 at Medium
  ```
  Rudraksh is banded G4 and is the only child at Hard, from rows, not a special case in code.

- **The pack builds.** Check: `uv run engine week assemble G3 T2W1 --actor nimish` →
  `5 named · 4 spare · 17 pages`, at `data/packs/G3-T2W1-practice/T2W1_pack.pdf`. Looked at two
  pages: each child's own name, their own QR, Medium is 2-digit and Hard is 3-digit.

- **No two children share a question.** Check:
  `psql "$DATABASE_URL" -Atc "select count(*) from sheet_template a join sheet_template b on a.id < b.id and a.item_ids && b.item_ids where a.week='T2W1' and b.week='T2W1' and a.child_id is not null and b.child_id is not null"` → `0`

- **The offline fallback works**, which is the only reason the pack exists today — the free tier's
  20 requests per model were spent. Check: `uv run engine bank fill SUB.2D.EXCH Medium --n 120
  --offline` → `accepted 120, rejected 0`, through the same verifier as the model path.

- **Bug found and fixed:** `bank recheck` compared missing-number questions against whole-equation
  predictors and wrongly flagged 30 of them. It now rebuilds each item through the same
  `verify.to_item` that made it, so the audit cannot drift from generation. Two regression tests,
  one of which edits a stored answer behind the engine's back and expects it caught.
  Check: `uv run engine bank recheck` → `0 mismatches` over the whole live bank.

- **Engine: 114 tests.** Check: `cd packages/engine && uv run pytest -q` → all pass.

- **The dashboard, driven end to end in a browser against the real database: 40 tests, two passes.**
  Check: `cd apps/web && npm run test:e2e` → `32 passed` then `8 passed`. Every action is asserted
  in the database, not just on screen: editing a difficulty changes the stored rule; a difficulty
  with no exchange ticked saves nothing; ratifying records who; removing a question writes the
  flag and the trigger retires it; changing a child's level stores the reason; approving marks the
  papers printed. The second pass runs with the sign-in bypass **off** and proves all seven routes
  redirect to sign-in — a gate only ever tested with the bypass on is not tested.

## Real assessment data received (2026-09-17)

16 children in `~/cornerstone/assessments/` — 11 in G2, 5 in G3, of whom Rudraksh is confirmed
Grade 4 and the only one. 37 usable papers plus 7 Olympiad booklets. Twelve scans carried no name
in the filename and were attributed by reading their printed headers; the manifest records who
each belongs to. Nothing was moved.

Two filename assumptions were wrong and were corrected by looking: in G3 the PDF is Aseem's
report and the WhatsApp images are the papers; in G2 the PDF is the paper and the WhatsApp images
are further pages in a different format. Both directions matter for the importer.

Confirmed by Nimish: Level B is above Level A, so B maps to L+ and A to L0.

## Code

- `engine/db.py` — the only module that opens a connection.
- `engine/loaders.py` — seed JSON to tables, upsert on the natural code, plus `orphans()` for the
  referential checks the schema cannot express (codes live in arrays).
- `engine/cli.py` — `engine load`, `engine load --check`.
- `engine/assess/tags.py` — taxonomy §12 case tags derived from generator parameters.
- macOS python.org build has no CA bundle; the engine venv must include `certifi`.

## N3 — legacy import and Child Growth, as a teacher reads it (2026-09-18)

Migration `20260918130000_graph_functions` applied: the six-state graph rule is SQL
(`rebuild_child_skill_state`, `next_difficulty`, `confirm_results`, `resolve_result`), so the CLI
and the app run one rule. Thresholds are rows (`state.min_events` 3, `state.min_observers` 2,
`next_sheet.promote_at` 0.8, `next_sheet.demote_below` 0.5).

- **Four Grade 2 children have ladders built from confirmed evidence.** Check:
  `psql "$DATABASE_URL" -Atc "select count(*), count(distinct child_id) from evidence_event where confirmed_by is not null"`
  → `218|4`. Blank answers carry `correct = null` and never count as attempts (rule 5):
  `select status, correct, count(*) from evidence_event e join item_result r on r.id = e.item_result_id group by 1,2`
  → `blank||7`, `correct|t|178`, `wrong|f|33`.

- **A rung can carry two skills and keeps a state per skill.** R9 (3-digit ±) holds Addition and
  Subtraction separately; for one child they differ (`stretch_ready` / `patterned_error`, mistake
  `M_FACT_PM10`). Check: `select child_id, rung_code, skill_code, state from child_skill_state
  where rung_code = 'R9'` → six rows, two per child.

- **`/growth/[id]` is one lane per skill, in the school's words, with the answers behind each
  step.** Names come from `rung.descriptor`, `skill.name`, `skill_set.name` and
  `misconception.name`; no code reaches the page. Check: `cd apps/web && AUTH_DEV_BYPASS=1 npx
  playwright test --project=screens` → `17 passed (8.1s)`, including *a child's ladder is in
  words, with the answers behind each rung*, which asserts no `R\d`, `X\d`, `M_…` or
  `AAA.BBB.CCC` token appears in the ladder and that clicking a step reveals a table with a
  *Child wrote* column. No sideways scroll at 400 px on `/growth` or a child page.

- **The double-import fault above is fixed, not just described.** `engine legacy dedupe` (chunk 1
  of `docs/superpowers/plans/2026-09-18-spine.md`) backfilled every capture's content hash and
  superseded every live capture but the best one per (sheet, file) pair, never deleting a row
  (rule 4). Check: `uv run engine legacy dedupe` → `28 captures given a content hash, 16
  superseded`; then `uv run engine graph` → `26 states`; then
  `psql -Atc "select count(*) from evidence_event e join item_result r on r.id=e.item_result_id
  join capture c on c.id=r.capture_id where c.superseded_by is null and e.confirmed_by is not
  null"` → `133` (was 218); and `select si.child_id, t.key->>'title', count(*) from capture c
  join sheet_instance si on si.id=c.sheet_instance_id join sheet_template t on t.id=si.sheet_template_id
  where c.superseded_by is null and exists (select 1 from item_result r where r.capture_id=c.id)
  group by 1,2 having count(*)>1` → zero rows. `import_scan` is idempotent on the file's content
  going forward (`file_sha256`, a partial unique index), so this cannot recur by re-running the
  same command twice.

## N3.1 — the spine, chunk 1: idempotent capture, Haiku reads, a budget the adapter refuses past (2026-09-19)

Plan: `docs/superpowers/plans/2026-09-18-spine.md`. ADR 0007 (learning loop), 0008 (engine as a
service; n8n moves to F3 now, not N7), 0009 (subject plugins). Migration
`20260919090000_service_foundations`: `capture.file_sha256`/`superseded_by`, `flow_run.model`/
`tokens_in`/`tokens_out`/`idempotency_key`/`request`, `prompt.subject`, and three new tables —
`subject`, `read_correction`, `child_reading_profile`. `rebuild_child_skill_state` and
`confirm_results` re-defined to read only live (non-superseded) captures.

- **The three active read prompts run on Haiku, not Sonnet** — the $10 burn's cause (HANDOFF.md,
  earlier session). Check: `psql -Atc "select purpose, model from prompt where active and purpose
  in ('read_cells','read_page','legacy_extract')"` → all three `claude-haiku-4-5`.

- **The adapter refuses a call before it is made once today's spend reaches the
  `llm.daily_budget_inr` threshold row (₹150 default), and prefers a subject-scoped prompt row
  over the shared one for the same purpose.** Check: `cd packages/engine && uv run pytest -q
  tests/test_llm.py` → `20 passed`, including a budget-refusal test that asserts zero `flow_run`
  rows are written for a refusal, and a real-database test of the subject-selection SQL itself.

- **A PDF renders in-process; `pdftoppm` is gone.** The September batch's transient subprocess
  failures (13 of 28 captures once held `status = 'error'`) cannot recur because there is no
  subprocess. Check: `uv run pytest -q tests/test_render_pdf.py` → `2 passed`; every previously
  `error` capture now renders and reads under `engine legacy import` (or, more precisely,
  already-imported ones are superseded correctly by `engine legacy dedupe` above).

- **`engine load` is unchanged in kind, larger by one table.** Check: `uv run engine load --check`
  → 13 rows printed including `subject 1`, `threshold 12`, `config 7`, `every code referenced
  resolves`, `unchanged on a second run`.

- **Full engine suite, including everything above.** Check: `cd packages/engine && uv run pytest -q`
  → `146 passed`.

- **Not yet built** (chunks 3–7 of the same plan): n8n is not installed; `read_correction` and
  `child_reading_profile` are empty tables, waiting on chunk 3's settle-flow write and chunk 6's
  rebuild; `engine/subjects/` does not exist yet — `subject.verifier = 'maths'` names a module chunk
  5 has not written; `/prescribe` `/assemble` `/render` are deliberately not built (below).

## N3.2 — the spine, chunk 2: the engine as a service (2026-09-19)

Plan: `docs/superpowers/plans/2026-09-18-spine.md` (chunk 2's own section there records two
deliberate departures from its original text and everything below in more detail). ADR 0008.
`packages/engine/engine/api/`: `app.py`, `deps.py`, `idempotency.py`, `models.py`,
`routes/{capture,children,graph,bank,runs}.py`. Migration `20260920090000_flow_run_result.sql`
(`flow_run.result jsonb`). `Dockerfile`, `.dockerignore`, `deploy/compose.yml`.

- **Every route sits behind `X-Engine-Key`, and an unconfigured key refuses everything rather
  than accepting anything.** Check: `cd packages/engine && uv run pytest -q tests/api/test_deps.py`
  → `6 passed`, including the case where `ENGINE_KEY` itself is unset or empty (500, not a silent
  401-that-could-have-been-200).

- **`run_idempotent` runs a route's function at most once per (tenant, flow, key); a call still
  `running` (a genuine concurrent duplicate) is refused, never double-run; a call that previously
  failed is retried, not permanently stuck.** Tested against the real partial unique index
  (`flow_run_idempotency_idx`), not a fake connection — a fake cannot reproduce
  `ON CONFLICT … WHERE … DO NOTHING`'s actual semantics. Check: `uv run pytest -q
  tests/api/test_idempotency.py` → `8 passed`. The `InProgress` exception is also proven to reach
  an HTTP caller as a 409, not an unhandled 500 — a distinct claim from "the Python exception is
  raised", caught only because both were tested (`test_capture_routes.py::…already_in_flight…`).

- **Verified for real, against the deployed container and the real database, not only in
  pytest.** `docker compose -f deploy/compose.yml build engine` → built; the running container's
  own `/health` → `{"ok": true}`, Docker's healthcheck → `healthy`; `POST /graph/rebuild` with the
  real `X-Engine-Key` → `{"states": 26, "already": false}` and a `flow_run` row with `flow =
  'graph_rebuild', trigger = 'http', status = 'ok'`; the same call repeated with the same
  `Idempotency-Key` → `{"states": 26, "already": true}`, and exactly one `flow_run` row exists for
  that key, not two.

- **A real bug this verification caught, that no unit test could have:** `db.py`'s `REPO_ROOT =
  Path(__file__).resolve().parents[3]` assumed the monorepo's directory depth and raised
  `IndexError` at import time inside the container, where the Dockerfile copies only `engine/`
  (`/app/engine/db.py` has nothing four levels above it) — every route imports `engine.db`
  transitively, so the whole process died before serving a request. Fixed (`_repo_root_for`, a
  pure function now unit-tested — `uv run pytest -q tests/test_db.py` → `3 passed`) and only found
  because chunk 2's own criteria insisted on a real `docker build` + a real container, not a mock.

- **`bank.fill` is not naturally idempotent** (unlike `import_scan`, chunk 1) — a fresh model call
  returns different items each time, so a retried `/bank/fill` HTTP call without the wrapper would
  silently double-spend model tokens. Check: `uv run pytest -q tests/api/test_bank_routes.py` →
  `5 passed`, including a test that a retried call asks the model exactly once.

- **Full API and engine suites.** Check: `cd packages/engine && uv run pytest -q tests/api` →
  `41 passed`; `uv run pytest -q` (the whole engine suite) → `182` collected, all green.

- **Deferred, not built: `/prescribe`, `/assemble`, `/render`.** They need an answer to "where
  does a rendered PDF live when the engine runs in a container" that nothing in chunks 1–4 needs
  yet (F3 read-and-respond never calls them) — building them without that answer is how a route
  ships with the wrong assumption baked into its shape. A later chunk states the storage answer
  first (a volume, or served back as bytes) and builds them against it.

- **Environment note, not a code defect:** this machine's Docker Desktop credential helper
  (`credsStore: "desktop"`) hangs indefinitely on a registry pull from a non-interactive session —
  it waits on a Keychain-mediated lookup with no UI to approve it. Worked around per-session via
  `DOCKER_CONFIG`/`DOCKER_HOST` pointed at a credential-helper-free config and the real socket
  (`~/.docker/run/docker.sock`); the user's own interactive terminal is unaffected. Recorded in
  case a future session hits the same silent hang and burns time on the wrong theory (network
  block) before checking `docker pull` directly.

## W1 gate 1 — every rung has a ratifiable skill-set spec (2026-09-19)

Nimish gave the yes on `BUILD-ORDER.md`'s six W1 gates in chat on 2026-09-19, including the
50-per-unit number and ADR 0010's design, clearing the block `HANDOFF.md` had recorded. Gate 1
scope: draft the 12 missing skill-set specs — R1–R4, R7, R8, R11–R14, X1, X2 — as rows in
`supabase/seed/skill_sets.json`, each with name, learning objective, philosophy, formats,
misconception codes, and a words rule plus a checkable rule for Easy/Medium/Hard/Advance.

- **All 16 rungs now have a skill-set row; the four already-drafted ones (R5, R6, R9, R10) are
  untouched.** For R7, R11, R13, X1 and X2 — where the substantive claim (mental strategy,
  rounding reasoning, "most efficient" method, an explanation, a diagnosis) is not something code
  can check — the row says so in its `philosophy` and names the validator route (a template-level
  check plus a ≤5 % item sample, never a per-item model call), per ADR 0009 and ADR 0010, rather
  than inventing a code verifier for it. Every `check` block still states what code *can* verify
  (the numeric or tick answer). All 16 rows load at `status = 'draft'`, awaiting Neha's and
  Achal's correction and Aseem's ratification (N1) — not yet ratified, so gate 1's fuller text
  ("every row `ratified`") is open; the count gate itself is closed.

  Check (the gate exactly as stated): `psql "$DATABASE_URL" -Atc "select count(*) from rung r
  where not exists (select 1 from skill_set s where s.rung_code = r.code)"` → `0`.

- **The loader accepts all 16 rows with no orphaned reference.** Every `misconception_codes` entry
  across the 12 new rows was checked by hand against `misconceptions.json` before writing, since
  `skill_set` is insert-only (Neha's and Achal's edits must never be overwritten) and a bad code
  would otherwise sit silently orphaned. Check: `cd packages/engine && uv run engine load --check`
  → `skill_set 16`, `every code referenced resolves`, `unchanged on a second run`.

- **A real regression this caught:** `tests/test_loaders.py`'s `EXPECTED` dict hardcoded
  `"skill_set": 4`; `test_every_table_has_the_expected_number_of_rows` would have failed the
  moment the loader ran with 16 rows in the seed. Fixed to `16` — the only code change gate 1
  needed. Check: `cd packages/engine && uv run pytest -q` → 186 passed, 0 failed (up from the
  182 recorded at N3.2; no other test assumed a skill_set count).

- **Not done:** gate 1's own fuller sentence — "every row `ratified`" — needs Neha and Achal to
  correct the 12 drafts and Aseem to ratify all 16, in the app; that is a human step, not a
  command. Gates 2–6 (the enumerator itself, the any-topic proof, per-template validation, the n8n
  flow, and the cost figure) are untouched, per `BUILD-ORDER.md` rule 1.

## W1 gate 2, chunk A — the arithmetic enumerator, zero model spend (2026-09-19)

Nimish chose "chunk A first" when gate 2 turned out to be two differently-sized jobs: (a) the
+/- units, which already had a working offline sampler ("the coin slot already exists"), needed
only a fix for a rung that mixes both operations; (b) 8 new question shapes (mental strategies,
word problems, budget, estimation, "most efficient method", explain, find-the-mistake) that need
their own generator wiring plus the sentence-template feature ADR 0010 promises — not built at
all yet. Chunk A is (a) only; (b) is deliberately not started.

- **A real, dangerous bug the new rungs exposed, fixed before it could fire:** `bank._sampled`
  silently fell back to rendering plain column arithmetic whenever a skill set's `formats` didn't
  overlap the sampler's four known shapes — which never happened with the original 4 skill sets
  (their formats always did overlap) but would have on R11 or X2 the moment anyone ran
  `--offline` on them: an "estimate first" or "find the mistake" unit would have silently filled
  with ordinary sums. It now refuses with a clear error instead. Check:
  `cd packages/engine && uv run pytest -q tests/test_bank.py -k sampled` → 2 passed (op-list
  candidates come back as real "+"/"-" pairs; a formats list with no sampler match raises).

- **`_sampled` and `verify.problems` accept `check.op` as a list**, needed because ADR 0010's own
  rungs are one skill_set per rung, not one per operation — R4 (2-digit ± without regrouping)
  mixes + and − in a single unit. Check: `uv run pytest -q tests/test_verify.py -k op_list` →
  2 passed.

- **`engine bank coverage`** (`bank.coverage()` + the CLI command gate 2 names) prints every one
  of the 64 skill_set x difficulty cells, zero cells included — the number gate 2's own text asks
  for, not a description. Check: `cd packages/engine && uv run engine bank coverage` → 64 units
  printed, 39 under 50 (the exact table is below).

- **25 of the 32 arithmetic-shaped units (the ones whose `check` is a plain op/digits/regroups
  rule reachable by the sampler) now hold >=50 active items, filled by
  `engine bank fill <code> <difficulty> --offline --n 50` — zero model calls. 7 fell short.**
  Check: `psql "$DATABASE_URL" -Atc "select coalesce(sum(cost_inr),0), count(*) from flow_run
  where flow = 'bank_fill' and created_at > now() - interval '20 minutes'"` → `0|0` — no flow_run
  row exists for this run because `--offline` never calls the model, a stronger proof than a cost
  of zero. Then `uv run engine bank recheck` → `0 mismatches` over the whole bank, old and new.
  Full table (Advance columns marked "native" were never attempted this chunk — R1's and R2's
  Advance bands use `missing_number`/`number_line_jumps` with no `digits`/`op` key, correctly
  routed to chunk B, not a shortfall):

  ```
  ADD.1D.WITHIN10   Easy 16  Medium 42  Hard  6                    — all three short
  ADD.1D.BRIDGE10   Easy 38  Medium 43  Hard  1   Advance  native  — all three attempted, short
  SUB.1D.WITHIN20   Easy 50  Medium 50  Hard 50   Advance 46       — one short
  ADD.2D.REG / SUB.2D.EXCH / ADD.3D.REG / SUB.3D.ZERO / ADDSUB.2D.NOREG: every band >=50
  ADDSUB.4D.ADV: Hard 50, Advance 50 (Easy/Medium are multi_add — native, chunk B, not attempted)
  ```

- **Two different causes behind the 7 short bands, both spec problems, not enumerator bugs:**
  (1) `ADD.1D.WITHIN10` Easy's own ceiling is only 16: at "sums to 5, both addends 1-9, no repeat
  digit" there are exactly 8 distinct (a, b) pairs, times the 2 formats the row declares
  (bare_sum, missing_number) = 16 — 16 is not a partial run, it is every item that rule can ever
  produce; Medium's ceiling is likewise well under 50. (2) `ADD.1D.WITHIN10` Medium/Hard and
  `ADD.1D.BRIDGE10` Medium/Hard share an *identical* effective rule (an unused `allow_zero_addend`
  flag doesn't change what the sampler draws), so the two bands compete for the same pool and
  whichever filled first — Medium, both times — took most of it, starving Hard (6 and 1). Item
  identity is the (template, a, b, op) tuple, not the skill_set/difficulty asking for it, so a
  pair generated under one band can never be generated again under a sibling. Neha, Achal and
  Aseem need to widen R1's number range (not just its band signatures) and give R1/R2's Medium and
  Hard bands genuinely distinct rules during ratification — a wording fix, not a code fix.

  `SUB.2D.EXCH` Medium/Hard now read 159/130 — the old per-item model path's rows (120/80, from
  the Sep 17 session, STATE.md above) plus this run's new enumerator items on top; the two paths
  cannot collide because they insert through the same dedup constraint.

- **A real regression this run caused, found by the full suite, fixed the same session:**
  `test_it_says_which_child_it_could_not_fill_rather_than_printing_a_short_paper` asserted
  `SUB.2D.EXCH` Advance was empty — true when the test was written, false now that chunk A filled
  every SUB.2D.EXCH band. Fixed by having the test retire those items inside its own rolled-back
  transaction rather than relying on a part of the shared bank staying empty forever. Check:
  `cd packages/engine && uv run pytest -q` → 191 passed, 0 failed (up from 186 at gate 1).

## W1 gate 2, chunk B — the native-generator units, still zero model spend (2026-09-19)

Nimish said "finish that" for chunk B. It split further once the code was actually read: 8 of the
9 remaining rungs (R1/R2's Advance bands, R7, R8, R11, R12's Easy/Medium, R13, R14, X2) already
had a hand-written generator function in `assess/items.py` needing only to be wired to a
skill_set row; X1 does not — its generator can only ever write one fixed, always-true claim about
two specific numbers, which ADR 0010 itself names as the reason explain-a-claim stays on the
per-item model path. X1 is therefore genuinely not part of this chunk's zero-cost story; it is
still 0 of 4 bands, honestly, not force-fit.

- **`bank.fill_native` (`engine bank fill <code> <difficulty> --native`) dispatches nine formats
  to their existing `assess/items.py` generator by `check['format']`, no model call, no
  verify.problems detour** (these generators are trusted code, the same guarantee the arithmetic
  sampler gets from its own round trip through `check`). Check:
  `cd packages/engine && uv run pytest -q tests/test_bank.py -k fill_native` → 27 passed.

- **Three real bugs found and fixed before they could ship, each with its own test:**
  1. `number_line_jumps(hi=20)` (tried for R2's Advance band) computed an impossible random
     range and crashed with a raw Python `ValueError` — its second jump is hard-coded to an
     11-39 two-digit number, a different scale than R2's "within 20." It now refuses clearly
     (`RuntimeError: … needs hi >= 54 …`) instead of crashing obscurely; R2 Advance stays
     unfilled rather than fed a nonsensical hi. Not a rewrite of the generator's number range —
     that would be inventing pedagogical content that is Aseem's call, not mine.
  2. `efficient_method` and `find_mistake` ignored the very parameter (`kind`, `digits`) that
     distinguishes STRATEGY.EFFICIENT's and REASON.FIND_MISTAKE's own difficulty bands — every
     band would have drawn from the same mixed pool. Both now take an optional parameter
     (default preserves the old random-choice behaviour for any other caller). Check:
     `uv run pytest -q tests/test_items.py -k "efficient_method or find_mistake"` → 6 passed.
  3. `fill_native`'s RNG was seeded from `(code, difficulty, attempt_number)` alone, so a second
     call for the same unit retraced the exact same sequence from attempt 1 — it could never top
     up a unit, only rediscover what a previous call had already inserted (this is what my own
     first test run collided with, against the real bank chunk B-1 had just filled). Fixed to a
     real per-call RNG. Check: `uv run pytest -q tests/test_bank.py -k produces_no_flow_run_row`
     plus the full `fill_native` suite above, both green against the real, now-fuller bank.

- **22 of the 23 units reachable this way, plus all 4 of REASON.FIND_MISTAKE (X2, filled
  separately after its `check` needed a `format`/`digits` fix — see below), now hold >=50 active
  items — 0₹ model spend for all of it.** Check: `psql "$DATABASE_URL" -Atc "select
  coalesce(sum(cost_inr),0), count(*) from flow_run where created_at > now() - interval '30
  minutes'"` → `0|0` — no flow_run row exists for any of chunk B's fills. Then
  `uv run engine bank recheck` → `0 mismatches` over the whole bank, chunk A and B and the
  original 4 together.

- **`ESTIMATE.ROUND10`, `ADDSUB.4D.ADV` (its multi-addend Easy/Medium bands) and
  `STRATEGY.EFFICIENT`'s `check` blocks needed a `format` key added** (they had `op`/`digits`/
  `kind` but nothing saying which generator to use — `_sampled`'s empty-intersection guard from
  chunk A would otherwise have refused them, correctly, rather than guess). `REASON.FIND_MISTAKE`
  needed the same plus its new `digits` key. Since none of these four rows had any items yet and
  `skill_set` is insert-only, the rows were deleted and `engine load` re-inserted the corrected
  version — the seed file stays the single source of truth. Check: `cd packages/engine && uv run
  engine load --check` → `skill_set 16`, `every code referenced resolves`.

- **`engine bank coverage` now reads 50 of 64 units at >=50 — 14 short.** Full remaining list:
  `ADD.1D.WITHIN10` (16, 42, 6, 24 — its own tiny "sums to 10" ceiling, not a bug, see chunk A),
  `ADD.1D.BRIDGE10` (38, 43, 1, and Advance still 0 — `number_line_jumps` needs a proper
  small-range generator, not built), `MENTAL.BRIDGE_EQ` Hard (48, one short of its own ceiling),
  `SUB.1D.WITHIN20` Advance (46, one short), and `REASON.EXPLAIN` (X1, all four bands still 0 —
  needs either new claim-template content or the real per-item model path, whichever Nimish
  chooses; not started).

- **Full engine suite: 227 passed, 0 failed** (up from 191 at gate 1, and including a fix to
  `tests/test_bank.py::test_coverage_…` whose "this cell is always empty" fixture cell was itself
  a casualty of chunk B filling `ADD.1D.WITHIN10` Advance).

## W1 gate 2, chunk C — closing out: 57 of 64, and the seven that arithmetic forbids (2026-09-19)

Nimish: "finish this and finalize so that we can move to the next workflow." Everything that
could be closed by engineering is closed. Seven units cannot be, for a reason no amount of code
changes, and that needs one decision from him (below).

- **X1 (`REASON.EXPLAIN`) is no longer stuck at zero: all four bands hold 50.** `explain_claim`
  had exactly one hardcoded claim (always true, always a 120-480 compensation pair). It now takes
  `a_range`, `claim_is_true` and `claim_topic`, giving it the four shapes its bands actually ask
  for — a true compensation claim, the same at 2-digit scale, a *false* claim the child must
  catch, and a claim about regrouping itself. Defaults reproduce the old behaviour exactly, which
  `blueprints.py`'s three callers depend on. Check: `uv run pytest -q tests/test_items.py -k
  explain_claim` → 5 passed, including that the true and false variants are distinct items.
  This keeps X1 on the zero-cost template path rather than the per-item model path ADR 0010
  allowed for it — the claim wording is a template with number slots, which is exactly what that
  ADR asks the model to write once; here it is written once in code instead, for ₹0.

- **R2's Advance band (`number_line_jumps` at hi=20) now works** — a `_bridge_jump` path draws
  the jump that crosses one ten (the strategy that rung teaches) instead of the 11-39 two-digit
  jump the full-scale version uses, which is what made hi=20 impossible before. Below hi=12 it
  still refuses with a sentence rather than a raw `randrange` error. Check:
  `uv run pytest -q tests/test_items.py -k number_line` → 3 passed (the small-range jump always
  lands on a ten and stays in range; the full-scale split is unchanged).

- **A band can now pin itself to one format** (`check.format` on the arithmetic path, mirroring
  what the native path already did). This is what stopped R1's and R2's Medium and Hard bands
  competing for one pool of sums: Medium is now the bare sum, Hard the same sums told as a story.
  Together with the seeding fix, this moved `ADD.1D.BRIDGE10` Easy 38 → 75, its Hard 1 → 45,
  `ADD.1D.WITHIN10` Hard 6 → 30, and `SUB.1D.WITHIN20` Advance 46 → 68.

- **`MENTAL.BRIDGE_EQ` Hard reached 50** by raising its balance-scale ceiling from 100 to 150:
  `balance_scale` draws its terms in tens below hi/2, so hi=100 allowed only {10,20,30,40} and
  capped the unit at exactly 48. A number in a draft row, not a code change.

- **Where gate 2 now stands: 57 of 64 units at >=50.** Check: `uv run engine bank coverage` →
  `64 units, 7 under 50`; `uv run engine bank recheck` → `0 mismatches`;
  `cd packages/engine && uv run pytest -q` → 235 passed, 0 failed.

- **The seven that could not reach 50 are capped by arithmetic, not engineering — and Nimish
  amended the gate rather than the ladder (ADR 0011).** "Adds within 10" has about 40 usable
  (a, b) pairs in total; four bands each wanting 50 distinct items need 200, which the numbers
  cannot supply however the code is written. The target is now "50, or the unit's whole
  enumerable universe, whichever is smaller", with the floor written as `min_items` on the band's
  own row so the gate stays one machine-checkable command. He rejected widening R1/R2's ranges
  (that redefines what the rung teaches — Aseem's call) and re-identifying word problems by their
  story (honest, but rewrites the key of every stored word problem and needs a migration).

- **Each floor was measured, not assumed.** A fill against each of the seven was re-run and
  accepted zero new items — the evidence that the count is the ceiling of what the rule can ever
  produce, not the point a run stopped at. Check: the run's output, `new=0` on six and `new=1` on
  the seventh (`ADD.1D.BRIDGE10` Hard, 45 → 46). Floors recorded: `ADD.1D.WITHIN10` 24/42/30/24,
  `ADD.1D.BRIDGE10` 43/46/35. ADR 0011 requires this evidence before any future floor is written,
  so the rule cannot decay into "the bar is whatever we got".

- **W1 GATE 2 IS CLOSED.** Check: `cd packages/engine && uv run engine bank coverage` →
  `64 units, 0 under their target`; `uv run engine bank recheck` → `0 mismatches`;
  `uv run pytest -q` → 236 passed, 0 failed.

- **Gate 6 is already satisfied, well inside its bar: the whole bank cost ₹0.** Check:
  `psql "$DATABASE_URL" -Atc "select coalesce(sum(cost_inr),0), count(*) from flow_run"` → `0|62`,
  against 3,373 live questions (`select count(*) from item where status='active' and
  skill_set_code is not null`). The bar was ₹50 for the whole 64-unit bank; every item in it was
  enumerated by code. The only model spend this design ever calls for is template judging
  (gate 4), which has not been run yet.

## W1 gate 3 — a new topic added as rows: multiplication (2026-09-19)

`BUILD-ORDER.md` names multiplication as this gate's own test case. `NUM.OPS.03 Multiplication &
times tables` already existed in the registry, so the topic needed a rung row, a skill-set row,
and the one sampler ADR 0010 prices in per *operation* (not per topic).

- **What the new topic actually cost in code**, against the gate's hope of "only `verify.py`,
  if anything": `verify.py` needed **nothing** — `problems()` reads the op generically,
  `REGROUPS` has no `×` so the regroup rule is skipped, and `_template` already emitted `MUL.*`.
  What it did need: `sample_mul` (~18 lines) and a `CONTEXTS_MUL` story list in
  `assess/items.py`, and a two-line `elif op == "×"` in `bank._sampled`. Everything else —
  the rung, the skill set, all four difficulty rules — is rows. A *second* multiplication topic
  now costs rows alone, which is what the gate is really testing.

- **A silent-corruption bug caught before it could fire.** `word_1step` picks a story first and
  then samples numbers in an if-plus/else-minus branch, so a `×` story added to `CONTEXTS_1STEP`
  would have been handed *subtraction* numbers — a multiplication word problem with a
  subtraction answer, which nothing downstream would have flagged. The `×` stories live in their
  own `CONTEXTS_MUL` list instead, and the word-problem path now raises a sentence naming the
  missing story list rather than an `IndexError` from inside `random.choice`.

- **All four multiplication bands hold 50 items, zero model spend.** Check:
  `uv run engine bank fill MUL.1D <band> --offline --n 50` → `accepted 50` ×4; a sample reads
  `59 × 8 = 472`, `12 × 7 = 84`, and "A shelf holds 84 books. How many books are there on 31
  shelves?" (2604). Then `uv run engine bank recheck` → `0 mismatches`, and
  `uv run engine bank coverage` → `68 units, 0 under their target`. Suite: 240 passed.

- **Known thinness, stated not hidden:** multiplication has no misconception predictors yet, so
  its items carry no wrong-answer diagnosis — `M.predict("×", …)` returns `{}` and the verifier
  drops unverifiable claims by design. `tags.derive` also returns early for any op that is not
  `+`/`-`, so × items carry the format-level tags but none of the regrouping dimensions. Both
  are additions for whenever multiplication is actually taught, not blockers for this gate.

- **Debt taken on knowingly, recorded not hidden:** `assess/items.py` is now over the 400-line
  limit aislop enforces (it gained six generators' worth of parameters and the bridge jump).
  Splitting it touches every import of `I.*` across the engine; not done mid-task, and it is the
  first thing to clean up before more generators land there.

## The whole skill map, and what kind of thing each question is (2026-09-19)

Nimish, after finding the registry held 37 of 244 skills: "Stop doing incomplete work. If you
are loading a table and if you are making the backend, build the whole thing for now with all
the information that we have." And: every question should carry a classification, with the
evaluation triggered off it.

- **The registry now holds the whole map, not the maths slice.** `supabase/seed/registry.json`
  is generated from the Skill Map Review artifact (built 2026-09-15) and never hand-edited.
  Migration `20260921090000_full_registry`. Check: `cd packages/engine && uv run engine load
  --check` →
  ```
  domain 14 · skill 244 · milestone 849 · learning_objective 1750 ·
  learning_objective_skill 2012 · activity 2216 · activity_skill 3711 ·
  report_item 885 · trait 56
  every code referenced resolves · unchanged on a second run
  ```
  Those counts match the source's own `counts` block exactly. `registry-num.json` is deleted —
  two sources of truth for the registry is how a third of a map got loaded in the first place.

- **Four kinds of material that had nowhere to live before, now tables**: the school's own
  learning objectives (with the same five-word `signal` vocabulary our items use), its activity
  plans (each with the teachers' own three-level mastery descriptors, `level_1/2/3`), its
  report-card lines, and the trait/pillar framework. `skill` also gained `skill_type`
  (`academic` 127 / `non_academic` 94 / `trait_behaviour` 23), `pillar`, `ncf`, `cg`.
  `skill_type` is load-bearing: a trait or value-education skill must never be handed to the
  question bank and auto-scored — the council review is explicit that scoring honesty is the
  kind of measurement the school's founding principle rejects.

- **A performance bug I introduced and fixed in the same pass:** the first full load took
  **2 min 46 s** — 11,000 single inserts, each a round trip to a remote database, and the test
  suite loads three times. Rewritten with `executemany`: **13 seconds for two full loads**
  (`engine load --check` runs it twice), same output, still idempotent.

- **Every question now says what kind of thing it is, and marking dispatches on that**
  (ADR 0012, migration `20260921093000_eval_type`). A Postgres enum with four values —
  `computable`, `closed_set`, `rule_governed`, `open_response` — declared on the skill set as a
  row and stamped onto each item at generation. `assess/evaluate.judge()` routes to the
  evaluator. Only two are built; `closed_set` and `rule_governed` raise rather than fall through
  to the arithmetic evaluator, because a question the engine cannot judge must never be quietly
  marked. Check: `uv run pytest -q tests/test_evaluate.py` → 9 passed, including that an unbuilt
  kind refuses and that an unrecognised wrong answer stays `wrong` with no diagnosis rather than
  being forced into the nearest known mistake.

- **Current split, from the database rather than from intent:** 14 skill sets `computable`
  (3,040 items), 3 `open_response` (600 items — explain-a-claim, find-the-mistake and
  choose-the-efficient-method, the three that ask for a sentence as well as a number). The three
  were identified by querying which items actually carry a free-text response, not by guessing.
  Check: `select eval_type, count(*) from item where status='active' group by 1`.

- **Suite: 249 passed, 0 failed; `engine bank recheck` → 0 mismatches.**

## W1 gates 4 and 5 — the reviewers, versioning, dimensional difficulty, and F1 in n8n (2026-09-19)

Nimish read an external "Assessment Engine — Technical Architecture" proposal and asked for three
of its points to be folded into gate 4 before n8n hardened anything: two narrow reviewers instead
of one blended validator (§8.2/8.3), difficulty as measured dimensions rather than a label (§7),
and immutable versioning with provenance (§15). All three are in, written into `BUILD-ORDER.md`
first (rule 5).

- **Two advisory reviewers, each a prompt row.** `pedagogy_review` (does this test the claimed
  skill, rung and signal?) and `language_review` (can a child of this grade read it?). Each judges
  the band's *rule* once plus a ≤5 % sample of its items — ADR 0010's economics, applied to
  review. Verdicts land in `item_review` with `acted_on_by` null: advice until a person acts.
  Check: `uv run pytest -q tests/test_review.py` → 6 passed, including that a reject never
  retires anything and that reviewing every item (the cost enumeration removed) is refused.

- **Scored against a hand-judged gold set, and the first real money spent.** Check:
  `uv run engine eval language_review` → `agreed 6/6 = 1.0 · right reason 6/6 · ₹0.1855`;
  `uv run engine eval pedagogy_review` → `agreed 5/6 = 0.83 · right reason 5/6 · ₹0.3815`.
  The single disagreement is a real judgment difference, not an error: on a 2-digit sum filed in
  a 3-digit band, I said *revise* (right skill, wrong band) and the reviewer said *reject*.
  Neha and Achal should settle it; `supabase/seed/validator_gold.json` is provisional until they do.

- **A bug in my own eval harness, found by disbelieving a bad score.** The first run scored
  pedagogy 4/6. Both disagreements were the harness's fault: it sent one skill set's context for
  gold cases spanning three, and blanked the band rule — then scored the reviewer for not knowing
  the rule it had been denied. Now one call per (skill set, band), each carrying its own rule.
  A harness that withholds the rule measures the harness.

- **Difficulty is checked as measured dimensions, not asserted.** `verify.dimension_problems`
  compares an item's own `tags` against its band's region, in `fill` and across the whole bank in
  `recheck`. `engine load --check` additionally refuses two bands of one skill set that declare
  the same region — the starvation that emptied R1's Hard band, now impossible to reintroduce.

- **It immediately found real drift, and the bank was wrong, not the check.** 93 items sat in
  bands whose rule they did not satisfy: when R1/R2/R3's bands were pinned to one format each,
  the items already in them had been generated under the old unpinned rule —
  `SUB.1D.WITHIN20` Hard says "a comparison word problem" and held 36 bare sums and missing-number
  equations. All 93 retired (not deleted), the units re-filled under the pinned rules, and the
  floors re-measured with fresh zero-accept evidence (ADR 0011): pinning makes each band correct
  but smaller, because it draws on one format's pool instead of three. New floors:
  `ADD.1D.WITHIN10` 24/22/24/24, `ADD.1D.BRIDGE10` —/43/45/35, `SUB.1D.WITHIN20` —/—/44/40.
  `ADD.1D.BRIDGE10` Easy cleared 50 outright and lost its floor.

- **Versioned rules and provenance.** Editing a skill-set rule files the old one in
  `skill_set_version`, bumps `version`, and withdraws its ratification — Aseem approved the rule
  he read, not the one that replaced it. Ratifying is not an edit and bumps nothing. Every item
  records `skill_set_version`, `generator`, `prompt_id` and `model`; the 3,574 items that predate
  this carry `generator = 'pre-provenance'` rather than a reconstructed story. Check:
  `uv run pytest -q tests/test_provenance.py` → 5 passed;
  `select count(*) from item where skill_set_version is null and skill_set_code is not null` → 0.

- **The misconception analyst (ADR 0012, external proposal §8.5): `engine bank unclassified`.**
  Wrong answers no named mistake explains, commonest first, with how many children wrote each.
  Empty until W3 reads real papers — the instrument exists before the data. For any subject
  beyond arithmetic it is the only way the mistake vocabulary grows. Check:
  `uv run pytest -q tests/test_unclassified.py` → 3 passed, against seeded results.

- **GATE 5: F1 lives in Nimish's own n8n.** `https://cornerstoneschool.app.n8n.cloud/workflow/F0i4ylZkD8zpOfH0`,
  exported to `n8n/workflows/f1-build-the-bank.json`. Schedule + webhook → `GET
  /bank/coverage?short_only=true` → per unit: `POST /bank/fill` (idempotency-keyed per unit per
  day) → language reviewer → pedagogy reviewer → email a person only if something was flagged.
  Two new endpoints carry it (`/bank/coverage`, `/bank/review`) so the *engine* decides what
  "short" means and n8n only forwards the answer.

- **`n8n/lint.py` enforces rule 3, and it has been seen to fail.** Check:
  `python n8n/lint.py n8n/workflows/*.json` → `ok — 10 nodes, no thinking, no prompt text, no
  secrets`; `uv run pytest -q tests/test_n8n_lint.py` → 9 passed, each breaking the real workflow
  one way (Code node, langchain node, prompt in a body, literal credential in an auth header, no
  trigger) and expecting it caught — plus that a sticky note may hold long prose and that every
  HTTP call goes to the engine and nowhere else.

- **The flow's routing proven by running it** with pinned data (execution 1, status success): the
  loop took both short units one at a time, the IF sent the one with `not_passed = 2` down the
  "ask a person" branch, and the loop closed with `noItemsLeft`.

- **Not done, and it is the honest gap in gate 5:** the live end-to-end run — "change a skill-set
  row and watch items appear with nobody typing a command" — has not happened, because n8n Cloud
  cannot reach `http://engine:8000` on this laptop. That needs the engine deployed or tunnelled;
  it is a hosting decision, not a workflow change, and `deploy/compose.yml` already runs both
  together for the case where they share a host.

- **Suite: 281 passed, 0 failed.** Total model spend for everything so far: see gate 6 below —
  the reviewers are the first real cost, and they are pennies.

## Environment

- Docker, Supabase CLI, psql, Node, Python 3.14 present; n8n not installed (Docker);
  `gh` authenticated as nimishshah1989, admin of org `cornerstonepune`.

## W1 gate 1 closed — all 17 specs ratified by name (2026-09-19)

Gate 1's fuller sentence ("every row `ratified`") was the last open line in W1. It is closed by
Nimish's own signature rather than Aseem's, by his instruction in chat and ADR 0013.

- **`engine ratify --by "Nimish Shah"` → `17 ratified, 0 still draft`.** New: `bank.ratify` (one
  `update … where status = 'draft' … returning code, version`) behind `engine ratify`, which also
  takes `--code` for a single set. The per-set button in the app is unchanged and stays the normal
  path; this is the bulk command a gate can quote.
  Check: `select status, count(*) from skill_set group by status` → `ratified 17`;
  `select distinct ratified_by from skill_set` → `Nimish Shah`.
- **The gate exactly as `BUILD-ORDER.md` states it:** `select count(*) from rung r where not
  exists (select 1 from skill_set s where s.rung_code = r.code)` → `0`, and no row is `draft`.
- **Ratification is per-version, and that is enforced by the database, not by discipline.** The
  trigger `internal.skill_set_version_on_change` withdraws it the moment any content column moves,
  so the 17 signatures refer to the exact words live today (`SUB.2D.EXCH` is at v15, R1–R3 at v2,
  the rest at v1). Check: `uv run pytest tests/test_provenance.py` → 6 passed, including the new
  `test_ratify_records_the_person_and_only_touches_drafts` (ratifies one set, then the rest, and
  proves an already-ratified row is not signed twice).
- **Suite: 282 passed, 0 failed** (up from 281). Check: `cd packages/engine && .venv/bin/python -m
  pytest` → `282 passed, 6 warnings in 80.55s`.
- **Stale counts corrected in `BUILD-ORDER.md`:** it said 16 rungs and 64 units, written before
  multiplication was added as the gate-3 proof. The ladder holds 17 rungs and 68 units, which is
  what `engine bank coverage` has been printing since gate 2.
- **A real defect this closed gate exposed, now fixed.** Running the full suite used to un-ratify
  `SUB.2D.EXCH` in the live database: `tests/test_loaders.py`'s
  `test_load_does_not_overwrite_a_skill_set_edited_in_the_app` commits a real edit to that row and
  restores it, and the versioning trigger withdrew the signature on both writes. Measured before the
  fix: `v33 ratified` → suite → `v35 draft, ratified_by null`. The restore now puts status and
  `ratified_by` back in a second statement that touches no content column (the trigger only fires on
  content). Measured after: `v35 ratified` → suite → `v37 ratified`, `0 drafts`. The version still
  advances by two per run, which is correct — the test really does write two versions of that rule.
- **Not resolved by this.** Ratification is a signature, not an answer to the three pedagogy
  questions `HANDOFF.md` carries: the pedagogy reviewer's objection to missing-number and
  word-problem items inside an exchange band (verdicts still in `item_review`), the gold set's
  band-vs-reject disagreement, and the G1 floors. Those still need Neha, Achal and Aseem.

## The mistake list becomes an engine output (2026-09-19, ADR 0014)

Nimish's instruction: the list of everything a child can get wrong on a learning objective is the
engine's job, not a teacher's checkbox column. Built in two halves, which is the whole point.

- **Code owns what code can compute.** `engine bank misconceptions SUB.2D.EXCH` →
  `computed  Easy 6 · Hard 7 · Medium 5 · Advance 6`, then the model's additions. The computed half
  comes from `assess/bands.py`: sample the numbers a band's own rule allows, build items with the
  same generators the bank uses, and read the misconception codes off them. No model, no cost, and
  it cannot drift from what the bank actually computes for a real item because it is the same code.
- **The model owns what code cannot** — how a child misreads a story, a method nobody has written a
  predictor for, a reasoning slip. It is told what code has already covered and asked only for the
  rest. On a pure-arithmetic set it now correctly finds almost nothing to add; on `WORD.1_2STEP` it
  added 4 (`engine bank misconceptions WORD.1_2STEP` → `11 computed by code, 4 added by the model,
  1 thrown away · ₹0.6053`).
- **The prompt's eval measures the job the prompt actually has** (rule 7). `engine eval
  misconception_list` → `0.75 of the model's proposals survived as additions over 3 skill sets ·
  claude-haiku-4-5 · ₹1.5877`, one set per kind chosen by a row (arithmetic / word / open-response),
  not by a list in code. Recall against the curated lists is **no longer an eval**: it became a
  property of arithmetic, so it is a test.
- **Version history, kept because it is the record of the loop.** v1 scored recall 0.40 against the
  curated lists, v2 0.53 — and then the design changed, because asking a model to rediscover what
  predictors can enumerate was the wrong question (CLAUDE.md rule 11). v3 asks only for the
  uncovered families; v4 makes the worked example optional (a reasoning mistake has no wrong number;
  v3 threw away 3 of 5 proposals on `REASON.EXPLAIN` for arithmetic that was never the point) and
  lets an example carry three or four addends (a multi-addend band could not state its own example
  and the whole reply was rejected by the schema). v1–v3 are inactive rows, not deleted.
- **Every check a proposal passes, in code:** its own stated correct answer must be right, or the
  entry is dropped; a wrong answer an existing predictor reproduces means the proposal *is* that
  misconception, not a new name for it; a claim of "you can see it in the answer alone" that no
  predictor reproduces is **downgraded** to the written working (or to an explanation when there is
  no number at all) rather than stored as if a marker could act on it. Check:
  `uv run pytest tests/test_spec.py` → 11 passed, all offline.
- **Three real defects the code half found in the specs themselves**, each fixed at its cause:
  - `ADDSUB.2D.NOREG` claimed `M_SMALL_FROM_LARGE`. Its four bands forbid exchange, where that
    method produces the *right* answer — unmarkable by definition. Removed from seed and row.
  - `SUB.3D.ZERO` claimed `M_ALIGN_LEFT`. All four of its bands are equal-length (3−3, 4−4), so
    misaligning unequal operands cannot occur. Removed. If the school wants that mistake tested here,
    the fix is a band with unequal-length operands — Aseem's call, and the list then regenerates
    itself.
  - `ADDSUB.4D.ADV` claimed `M_CONCAT` and its multi-addend bands had no predictor for it, and
    `WORD.BUDGET` claimed `M_WRONG_OP` with nothing computing it. Both are real mistakes, so the
    predictors were written: `misconceptions.multi_concat` (column totals written out side by side
    with three or more addends) and the wrong-operation answer in `items.word_budget`.
  - The test that finds this class of defect is `test_code_finds_every_computable_mistake_a_curated_list_names`:
    for every skill set with numbers, what code reaches must include every curated code a predictor
    can produce at all. It is the guard against a spec claiming more than the engine can mark.
  - **`ADDSUB.2D.NOREG` and `SUB.3D.ZERO` went back to `draft`** when their lists changed — the
    trigger working — and were re-signed on 2026-09-20. Check: `engine ratify --by "Nimish Shah"` →
    `2 ratified, 0 still draft`; `select status, count(*) from skill_set group by status` →
    `ratified 17`.
- **Modules split along real responsibilities** (CLAUDE.md rule 11, aislop's 400-line ceiling):
  `engine/spec.py` (the spec a person approves, its ratification, its mistake list — 197 lines),
  `engine/assess/bands.py` (a band's rule → its numbers, its items, its reachable mistakes),
  `engine/cli_legacy.py` (N3's commands). `bank.py` 520 → 309, `cli.py` 454 → 367, both under the
  ceiling. `tests/test_spec.py` mirrors the new module.
- **Nothing has been applied to any skill set.** `--apply` unions the proposals into the set (it can
  never remove a curated code) and withdraws its ratification, so it waits for Nimish's word. Check:
  `select count(*) from misconception where source like 'misconception_list%'` → `0`.
- **Suite: 291 passed, 0 failed.** `engine load --check` → `unchanged on a second run`;
  `engine bank recheck` → `0 mismatches`. Model spend for the whole day's work on this: ₹11.
- **Still open, and it is a style decision, not a defect:** every Python file in the engine trips
  aislop's `python-formatting` warning, because the repo has never adopted `ruff format`. Measured
  before deciding: on two files the reformat is 536 diff lines, and it explodes the misconception
  registry from one readable line per mistake into five, which is the layout the vocabulary is read
  from. It needs Nimish's call — adopt the formatter and accept that, or record the exception in
  `.aislop/config.yaml` with the reason. `assess/items.py` carries the engine's oldest debt, now measured
  exactly: 49 ruff E701/E702 errors (the prototype's one-line style), 3 functions over the 6-parameter
  ceiling and 490 lines against a 400-line ceiling. Fixed there this session: an unused import, two
  f-strings with no placeholders, and the missing wrong-operation predictor. The rest is frozen and
  named, not inherited silently — `ruff format` would clear the 49 but grow the file past 700, so the
  honest order is split first, format second: a warning aislop itself marks unfixable, surfaced here per `AISLOP.md`'s ladder. Its real
  cause is that per-format generators and their story text belong in rows (rule 1, ADR 0010), which
  is a design thread with its own ADR, not a line-count shuffle.

## A goal is now runnable, and it found four more defects (2026-09-20, ADR 0015)

Nimish: "with every test you are finding an error — how do we know that we don't have any more
errors", then "we need to start having a very specific goal for every task/milestone … till 100%
accuracy is achieved." Two commands answer those two questions.

- **`bin/engine goal w1-build-the-bank` → `10/10 scenarios met the bar completely`,
  `5/5 criteria met · GOAL ACHIEVED`.** The goal file (`goals/w1-build-the-bank.yaml`) states in one
  sentence what W1 must do, then proves it on ten real requests — two-digit exchange at Hard and at
  Easy, three-digit across a zero, two-digit regrouping, a foundational rung with a small universe,
  multiplication (a topic added as rows only), four addends, a word problem, a budget, find-the-
  mistake. Each is checked *independently of the code that answered it*: every answer recomputed from
  the numbers, every question re-measured against its band's rule, every wrong answer mapped to a
  named mistake, no duplicates, nothing stored. Every scenario reported
  `produced=asked  answers_recomputed=asked  off_rule=0  undiagnosed=0  distinct=asked`.
- **`bin/engine audit` → `12 invariants checked, 0 violations`.** Twelve named properties of every
  row, in one sweep, so a new class of bug becomes an invariant rather than a test that trips over it
  by luck. It runs from any directory (`bin/engine`, CLAUDE.md rule 13) — the `cd packages/engine`
  form was giving Nimish shell errors.

**Four defects found by running them, each fixed at its cause:**

1. **Multiplication questions could not be diagnosed at all.** `MUL.1D` produced 20 correct, on-rule,
   distinct questions of which **14 had no named mistake to mark against**: `M.predict` had tables for
   `+` and `-` only, so every multiplication distractor was empty and a child's wrong answer could
   only ever be "wrong". Fixed by writing the predictors — `M_MUL_NO_CARRY`, `M_MUL_CONCAT`,
   `M_MUL_CARRY_FIRST`, `M_MUL_ONES_ONLY`, `M_MUL_ROW_OUT`, `M_WRONG_OP` — with their vocabulary rows.
   Check: `M.predict("×", 56, 3)` → `{M_MUL_CONCAT: 1518, M_MUL_ONES_ONLY: 18, M_MUL_ROW_OUT: 112, …}`,
   and the scenario now reports `undiagnosed=0`.
2. **The `misconception.op` constraint had no `×`** (it predated the multiplication rung), so the
   vocabulary had nowhere to put those rows. Migration `20260922090000_misconception_multiply.sql`.
3. **1,172 live items named six mistakes that were not in the vocabulary** — `M_ADD_INSTEAD` (476),
   `M_ONE_STEP_ONLY` (300), `M_SUM_ONLY` (200), `M_ADD_ALL` (148), `M_EQUALS_MEANS_ANSWER` (148),
   `M_FACT_PM100` (100). The generators had invented them inline and nothing checked. All six now have
   rows with names, examples and repair hints, and **an unknown code can no longer reach an item**:
   `bank._strip_unnamed` drops it at insert and counts it as `unnamed_distractor_dropped`, because the
   marker, the graph and the teacher's screen all read the vocabulary by code.
4. **The skill-set screen asked for `op = 'both'`**, a value the data has never used (it is `'any'`),
   so every operation-independent mistake was invisible in the app. One-word fix in
   `apps/web/lib/queries.ts`.

**And one test was hiding a defect rather than catching it:**
`test_every_seeded_answer_lookup_code_has_a_predictor` re-typed the union of predictor tables inside
itself, so it could not see that `MUL_PREDICTORS` did not exist. Replaced by one registry
(`M.PREDICTED`) plus the audit invariant *every answer-lookup code is computed somewhere*, which also
covers the codes the generators compute inline — the case the old test could never have caught.

**Suite: 294 passed** (up from 291). `tests/test_goal.py` runs the ten scenarios and the twelve
invariants, so the goal is defended in CI and not only by someone remembering to type it.

**What these two commands do NOT cover — the honest list of what we still do not know:**
- **W3's reading accuracy.** Nothing yet measures how well a scanned paper is read; 10 of the 84 real
  sheets have been through a first reader and no number was recorded. W3 needs its own goal file with
  an accuracy bar *before* the reader is built (ADR 0015).
- **W2 and W4 have no goal file**, so "assemble and print" and "close the loop" have no functional
  bar yet.
- **The app.** `apps/web` has Playwright screenshot tests; no scenario checks that what a teacher
  sees matches what the engine knows. The `op = 'both'` bug lived there for exactly that reason.
- **Pedagogy.** Whether a band's rule is the right thing to teach, and the three open questions in
  `HANDOFF.md`, are Neha's, Achal's and Aseem's. No command can close them.
- **Prompt quality beyond its own eval.** `misconception_list` scores 0.75 on additions and the two
  reviewers 6/6 and 5/6 against a provisional gold set; those numbers bound what the model is
  trusted for, they do not prove it right.

## Style is machine-enforced, and three "flaky" failures had one cause (2026-09-20)

- **`ruff format` adopted, `ruff check` pinned to the classes that are defects.** `line-length = 110`
  (the width this engine was written at; 88 would rewrap every line and call it formatting), the
  predictor registries wrapped in `# fmt: off` because one line per misconception is the point, and
  `select = ["E", "W", "F", "I"]` with `E501` left to the formatter. That cleared 49 real E701/E702
  errors in `assess/items.py`, three unused imports, two ambiguous `l` variables and a lambda
  assignment. CI now runs `ruff format --check` and `ruff check` before the suite, so the style
  cannot drift back. Check: `uv run ruff check engine tests` → `All checks passed!`;
  `uv run ruff format --check engine tests` → `72 files already formatted`.
- **`assess/words.py` split out of `items.py`** — the stories, the names and the three word-problem
  generators, whose real home is a row (ADR 0010) and which are now one visible file rather than a
  tail on a catalogue. `items.py` is still 741 lines against aislop's 400 because formatting expanded
  its dense one-line style; the remaining fix is rows, not another split, and it is named here rather
  than gamed.
- **Three intermittent failures — `test_legacy`, `test_loaders`, and a scenario — had one cause
  between them: a test that committed to a live spec row, plus me running two suites at once.**
  `test_load_does_not_overwrite_a_skill_set_edited_in_the_app` edited `SUB.2D.EXCH`, committed so
  that `load_all()`'s own connection could see it, and restored it in a `finally`. Two runs at once
  left the row edited and unratified, and every other test that read it failed in ways that looked
  like their own bugs. It now calls `loaders._skill_sets(conn, tenant)` on its own connection and
  rolls back: same clause proved, nothing written. Check: three consecutive full runs →
  `294 passed` each, and `engine audit` → `0 violations` after.
- **A real gap that flake exposed: `fill_native` had no in-batch duplicate guard.** Its only defence
  was the insert's conflict clause, so a dry run — a scenario, an eval — could hand back a set with a
  repeat in it. It now keeps the same `seen` set `fill` does. Check: six consecutive dry runs of
  `WORD.1_2STEP Easy` → `produced 20  distinct 20` every time; before, one in roughly five had 19
  distinct.
- **`bin/engine goal w1-build-the-bank` → `10/10 scenarios`, `5/5 criteria`, `GOAL ACHIEVED`** after
  all of the above. Suite 294 passed, audit 12/12 clean.

## The mistake lists applied to all 17 specs (2026-09-20)

Nimish ran `bank misconceptions WORD.1_2STEP --apply` himself, which exposed two defects in the
apply path before the rest were touched. Both fixed, then the whole ladder was applied.

- **The generated codes were unusable.** `_code_for` slugged the model's whole sentence and produced
  `M_MISCONCEPTION_S_DEMAND_ANSWERED_THE_Q` — a join key the graph, prescriptions and every screen
  would have carried forever. It now takes the first three words that mean something, never cutting
  mid-word: `M_USES_WRONG_OPERATION`, `M_PICKS_EXTRA_NUMBER`, `M_READS_TWO_STEP`. The five rows from
  that first apply were deleted and re-proposed; two later codes cut at the 30-character cap were
  renamed in the vocabulary and in every spec that referenced them.
- **Prompt v5: the name is a label, not a sentence** (six words, 60 characters), and the model is now
  shown **every name in the vocabulary**, not only the codes this band computes — because a mistake in
  reading a story has no wrong number to match on, so the only way to stop a second name for it is to
  show the first. Measured on `WORD.1_2STEP`: 5 proposals of which several duplicated existing
  mistakes, down to 1 genuinely new.
- **`--computed-only`: the free half, applied to all 17 specs.** `engine bank misconceptions <set>
  --computed-only` unions what code can already mark against, with no model call. **58 codes added
  across 12 specs at ₹0** — mistakes the marker has been diagnosing while the spec a person approves
  never mentioned them.
- **The model half applied to the seven sets arithmetic cannot reach** (reasoning, strategy, mental,
  estimate, budget, word problems): **26 engine-proposed mistakes now in the vocabulary**, every one
  `working`, `explanation` or `teacher` — none claims to be markable from the answer alone, because
  none has a reproducible number. Total spend ₹4.1.
- **A defect the dropped counter caught in my own checker:** `WORD.BUDGET` threw away 5 of 5
  proposals as "its own arithmetic is wrong" — and the arithmetic was mine. A budget question is a
  chain (`8000 − 25 − 40 − …`) and the checker read only its first two numbers. `M.chain` now folds
  left over however many numbers a question has. After the fix: 3 added, 3 dropped. The 3 that remain
  dropped mix operations in one example (per-child multiplication inside a subtraction chain), which a
  single `op` field cannot express — named here, not hidden.
- **All 17 ratified as `Nimish Shah (engine-derived list, applied 2026-09-20)`** — his instruction to
  finish, with the full list in front of him, and the attribution says the list was derived rather
  than read line by line. Editing any spec withdraws it as usual.
- **The vocabulary is now a table the seed does not own outright** (65 rows: 39 seeded, 26 proposed),
  so `test_every_table_has_the_expected_number_of_rows` no longer asserts an exact count for it. The
  seeded rows are a floor and each must be present — which is the stronger claim, and it will hold
  when `engine bank unclassified` starts adding what children actually write.
- **Green after all of it:** `bin/engine goal w1-build-the-bank` → `10/10 scenarios`, `5/5 criteria`,
  `GOAL ACHIEVED`; `bin/engine audit` → `12 invariants, 0 violations`; **295 passed**;
  `uv run ruff check engine tests` → `All checks passed!`.

## W2 — assemble and print: the week runner, the endpoints, F2 (2026-09-20)

W2's goal was written before its code (ADR 0015). Building against it, in the order the goal named.

- **`scenarios_week.py` — eleven scenarios that build a real week** for a throwaway section
  (`GOALSEC`), inside the caller's transaction, rolled back: prescribe, assemble, store, then read the
  properties off the rows the real path wrote. **Eight of nine passed on the first run**, which is
  what the parts' own tests had earned; the two failures were both real and both mine to fix.
- **The one product failure was the class register.** `a real class of sixteen gets sixteen different
  papers` → `children=16  papers=13  questions_needed=216  questions_held=159  short=3`. A week draws
  without replacement across a class, so one unit must hold `(children + spares) × items_per_sheet`.
  The bank's target was 50 — a round number with no relationship to a class list. **ADR 0016: a unit's
  target is what a class needs in a week**, every term a config row (`bank.class_size = 16`). Then the
  enumerator filled every short unit: **12,633 live questions, 68 of 68 units at target, ₹0**.
  Check: `engine bank coverage` → `68 units, 0 under their target`.
- **Thirteen units cannot reach it, and all thirteen are Grade 1 rungs** whose numbers genuinely run
  out — `ADD.1D.WITHIN10` holds 22–24 questions in total against a class need of 216. Four recorded a
  fresh measured ceiling as `min_items` (ADR 0011's evidence rule: a second fill that accepts nothing).
  So a Grade 1 class **cannot** have sixteen different papers in one week, and the engine must say so
  rather than print short ones. That is now its own scenario — *a Grade 1 class is told the rung is too
  small, never handed short papers* — so the limit is checked, not discovered in a classroom. The ways
  out are the school's: fewer questions per sheet for Grade 1, a wider rung, or accepted sharing.
- **The other failure was in my own check**: the exposure-window scenario cleared the first week's
  sheets so it could rebuild, which a prescription's foreign key rightly refused. It now builds **two
  consecutive weeks** for three children — the real thing a school does — and asserts nothing from
  week one comes back in week two. `children_checked_across_two_weeks=3  window_days=21`.
- **Three engine endpoints, because n8n never thinks** (rule 3): `POST /week/prescribe`,
  `/week/assemble`, `/week/render`, each thin, idempotency-keyed, calling the same functions the CLI
  calls. Check: `uv run pytest tests/api/test_week_routes.py` → 2 passed, including *the same week
  assembled twice is one week* (`already: true`, identical QR codes — a retry must never print a
  second set).
- **F2 exists and lints:** `n8n/workflows/f2-assemble-and-print.json` — Wednesday's declaration or a
  webhook → prescribe → assemble → **if any child was left without a paper, email a person and print
  nothing for them** → otherwise render the pack and ask the teacher to approve. Check:
  `python n8n/lint.py n8n/workflows/*.json` → `f2-assemble-and-print.json: ok — 10 nodes, no thinking,
  no prompt text, no secrets`.
- **The teacher's approval is now a guarantee, not a label.** `print_status = 'printed'` was a string
  any code could set; migration `20260923090000_print_needs_an_approver.sql` adds `approved_by` /
  `approved_at` and a check constraint, so **the database refuses a printed sheet that cannot say who
  allowed it**. `assemble.approve` is one tap for a class (N7 — a teacher's attention is the scarcest
  thing in the school), exposed as `POST /week/approve` so the screen and the flow use one
  implementation, and the Worksheets screen's one-tap action now writes the signed-in staff member's
  email with it. Checks: `uv run pytest tests/api/test_week_routes.py` → 4 passed, including *a sheet
  cannot be printed without someone approving it* (a `CheckViolation` is the assertion) and *approving
  the week names the person on every sheet*; plus W2's own scenario *nothing prints until a person
  approves* → `sheets=6  approved=6  by='a test'`.
- **The Grade 1 limit is proved rather than promised:** *a Grade 1 class is told the rung is too small,
  never handed short papers* → `children=16  papers=2  named_short=14  skill_set=ADD.1D.WITHIN10`.
  Fourteen of sixteen children are named with what was missing, and nothing is printed for them.
- **A flake that had cost three sessions' confusion is closed.** `test_legacy`'s evidence assertion
  compared a *sequence* against a query ordered only by `rung_code`, where every row was `R5` — so
  Postgres was free to hand them back in any order, and it failed about one run in three. It asserts
  the tally now. The app's own evidence read is properly ordered (`order by date, item_key`), so there
  was no product bug behind it. Three consecutive full runs clean.

- **Two things the new target broke in the suite, both corrected at the cause.**
  `test_fill_native_produces_items_for_every_native_unit` demanded five new questions from every
  native unit unconditionally — but `MENTAL.BRIDGE_EQ Easy` is now at its measured ceiling of 145, so
  a further fill *must* accept nothing. It asserts "five, or nothing and the band says why
  (`min_items`)". And `test_coverage_targets_50_by_default…` asserted the round number the decision
  replaced; it now reads the class need from the rows and checks a ceiling unit keeps its own.
- **My own migration was too strict and history caught it.** The approval constraint gated every
  status, so a legacy paper (N3) — entered after a child had already done it, on paper nobody printed
  here, landing as `returned` with no one to name — was refused. Narrowed to `print_status <>
  'printed' or approved_by is not null`: the gate is about printing, not about history. Three legacy
  tests were the ones that said so.
- **Suite: 300 passed** (up from 295: the week routes, the approval gate both ways, and the eleventh
  W2 scenario).

## A derived counter in the hot path deadlocked two classes (2026-09-20)

Found by timing W2's scenarios while a goal run was building weeks in another connection — two real
week builders at once, which is what a school does when two teachers declare on the same Wednesday,
or when F2 fires for two sections.

- **`assemble._store` incremented `item.times_used` for every question it handed out.** Two builders
  touching the same unit deadlocked on those rows. Ordering the update by id did not fix it —
  Postgres takes `FOR UPDATE` locks in *scan* order, not in the order of the `ORDER BY` — and once the
  update was ordered the deadlock simply moved to `item_exposure`'s index.
- **The counter is derived, so it moved to Ring B.** `graph.refresh_item_usage` computes it from
  `item_exposure`, which already records every handout row by row, and `engine graph` calls it. The
  hot path now takes no row locks at all. What the counter feeds is the pool's ordering — spreading
  the load across a unit — so being one rebuild behind costs nothing. This is what CLAUDE.md's Ring B
  already said: a derived number is a pure function of Ring A, rebuildable at any time, and it had no
  business being written by a concurrent path in Ring A.
- **Checked by a test that fails against the old code:**
  `tests/test_week.py::test_two_classes_assembled_at_the_same_moment_both_finish` builds two weeks in
  two threads on two connections. Against the previous query it raised `DeadlockDetected` (seen on the
  first of three attempts, then intermittently — a deadlock needs the interleaving); with the counter
  derived it passed **five runs out of five**. It is the one test here that commits, so it uses a
  section of its own per run and deactivates its children afterwards rather than deleting them —
  `evidence_event` is append-only and refuses a cascading delete (rule 4), which is also what a school
  does when a child leaves.
- **Suite: 301 passed.** `engine audit` → `12 invariants, 0 violations`.

## W3 opens: its goal written before its reader, and red on purpose (2026-09-20)

BUILD-ORDER rule "W2, W3 and W4 must have their goal files written before their work starts"
(ADR 0015). `goals/w3-read-and-graph.yaml` states W3's sentence, 17 scenarios and 4 criteria.
Nothing of the reader is built: the bar's numbers are proposed and wait on Nimish's yes.

- **W1, W2 and the audit were all green before any of this was written.** Check:
  `bin/engine goal w1-build-the-bank` → `10/10 scenarios · 5/5 criteria · GOAL ACHIEVED`;
  `bin/engine goal w2-assemble-and-print` → `12/12 scenarios · 4/4 criteria · GOAL ACHIEVED`;
  `bin/engine audit` → `12 invariants checked, 0 violations`. Suite `301 passed`.

- **The corpus, counted rather than described.** `~/cornerstone/assessments` holds 84 files /
  194 pages. In scope for reading: **118 pages across 72 files**. Out: 66 pages of SOF Olympiad
  booklets across 7 files (multiple-choice across the whole syllabus — `manifest.md` says only
  their add/sub items map to a rung) and 10 pages of Aseem's five typed Grade 3 reports, which are
  the gold and not the input. Check: a `pymupdf` page count over the tree →
  `files: 84   total pages: 194`, then classified → `paper 72/118, olympiad 7/66, report 5/10`,
  and `paper pages whose PDF already has a text layer: 0`. Every response must come through vision.

- **Two reading regimes, not one.** 80 pages are flat scans of a printed paper answered in pen
  (regime A); 38 are phone photos — angled, page curved, answers in pencil, with the teacher's own
  tick and cross in pen beside the child's answer (regime B). Confirmed by eye on
  `G3/1. Kabir/Assessment 0/WhatsApp Image 2026-08-16 at 18.02.42.jpeg`.

- **What has actually been read so far: 10 captures, all regime A, 138 responses.** Check:
  `psql -Atc "select c.status, count(*) from capture c where c.superseded_by is null group by 1"`
  → `processed 10`, `error 2`. Both errors are one cause — `claude-sonnet-5 returned HTTP 400:
  Your credit balance is too low`. No regime-B page has ever been read.
  `select count(*) from item_result r join capture c on c.id=r.capture_id where c.superseded_by is
  null` → `138`, and `select round(read_confidence,2), count(*) …` → `null|138`: the reader does
  not report its own confidence, so "the reader flagged it" does not yet exist as a distinction.

- **The first hand-check of a read against the page it came from (Advika, Cambridge Level A,
  2 pages).** Rendered at 150 dpi and compared response by response against the 24 rows in
  `item_result`:
  - **24 of 24 responses the engine emitted were read exactly right** — every digit and both
    blanks. 148+7→155, 236+9→245, 357+8→365, 425+6→431, 348+27→374, 476+58→534, 285+96→281,
    165−7→158, 243−8→235, 352−6→346, 471−9→462, 425−38→397, 563−47→516, 342−58→384, 250+[150],
    45+[5], [80]−20, 100−[30], estimate 282, 763+427→1190, 1190+38→1228, Q9 blank, Q10 blank.
    Two of those are diagnostic gold: 763+427 is the child adding where the question subtracts.
  - **But the page holds 27 responses.** Q5's three filled boxes (`0`, `52`, `72`) became one row
    reading `72`; Q7's estimate and total became one. **Three responses never got a row at all.**
  - **Systematic, not a one-off.** All three children who sat that paper produced exactly 24 rows:
    `select c.path, count(*) … where c.path like '%sept. 1st%'` → Advika 24, Heian 24, Hridhima 24.
  - So the failure mode is not misreading digits — it is not emitting a row. A bar phrased as
    "% of responses read correctly" scores this sheet 100% and hides the hole. This is why the goal
    file carries two separate numbers and a recall bar of 100 rather than 97.
  - It is the same defect class STATE.md recorded on 2026-09-17 ("`legacy_extract` needs a `part`
    field — Q1's four lettered sub-answers arrived crammed into one string"): fixed for lettered
    parts, still open for in-line boxes and for two-part questions like estimate-then-total.

- **The goal is declared and red, which is the state it is supposed to open in.** Check:
  `bin/engine goal w3-read-and-graph` → exit 1,
  `2/4 criteria met · … · 17 scenarios short of the bar`; every scenario reports
  `no runner for a 'read' scenario yet — this goal is declared, not met`, and the two failing
  criteria are the two things W3 has to build (`n8n/workflows/f3-read-and-graph.json`,
  `engine read accuracy`).

## W3 gate 1 found: the papers themselves are the defect, not the reader (2026-09-20)

Nimish: "for every grade 2 and grade 3 student in that drive we have, at least 3 to 4 assignments,
so make sure that you are not missing out on anything." Counting from disk rather than from
`manifest.md` proved him right and the manifest wrong.

- **52 sittings across 16 children, not the manifest's 37.** Check: a per-child inventory over
  `~/cornerstone/assessments`, attributing every loose file by the manifest's own table →
  `sittings-per-child distribution: {1: 2, 2: 3, 3: 4, 4: 3, 5: 4}`, `children: 16`,
  `total sittings: 52`, `unattributed files: none`. The manifest omits the WhatsApp images
  entirely — 20 Grade 3 baseline pages and 15 Grade 2 extra pages. It is data documentation kept
  outside git, so it is flagged here rather than rewritten.

- **The Grade 2 Cambridge paper runs at four levels, not two.** Check: a contact sheet of the
  printed header band of all ten `sept. 1st` PDFs → **Level A** ×4, **Level B** ×4, **Level D** ×1,
  and one whose header is cropped but whose Q1 (`62 + 5`, `71 + 6`) matches neither `G2-CAM-A`
  (`148 + 7`) nor `G2-CAM-B` (`48 + 7`), so a fourth form exists. Only A and B are in the database.
  Seven of the ten Grade 2 children who sat it are therefore unreadable today.

- **`G2-CAM-B` is correctly entered, as far as its first page.** Check: Q1–Q5 on a real Level B page
  are `48+7, 36+9, 27+8, 55+6 / 154+8, 267+5, 348+9, 236+7 / 63−8, 72−5, 84−6, 91−7 / 52−27, 74−38,
  61−45, 83−59 / 165−7, 243−8, 276−9, 354−6` — 20 answers, all single-box, matching the 20 slots the
  row holds for that page. Page 2 (`6a, 6b, 7, 8`) is not yet checked.

- **Why a wrong slot count loses answers silently.** `legacy.import_scan` looks each read up by
  `n`+`part` in `paper_rows`' `by_key`; a key with no slot appends to `summary["unmatched"]` and
  `continue`s. So the model may well have read all 27 of `G2-CAM-A`'s answers — the code had
  nowhere to put three of them. The root cause is the paper's entry, not the prompt or the model.

- **The full paper inventory is `docs/w3-paper-inventory.md`**: 14 distinct papers, of which 4 are
  entered (1 proven wrong, 2 unchecked) and **10 have never been entered** — including the Grade 3
  16-question baseline that all five of Aseem's gold reports are written from, and where
  `8500 − 3647 = 5147` lives. The gold set for the whole pipeline is behind this gate.

- **The child with the fewest papers is on the paper nobody entered.** One child has a single
  sitting, on Level D, and wrote `4+3=55`, `6+2=45`, `5+4=35`, `3+5=61`, `9+4=49` with no working
  anywhere on the page. The answers bear no relation to the operands: that child is not computing
  at all. It is the sharpest diagnostic signal in the corpus and the engine cannot currently see it.

- **Two test children were left active in the live roster.** `select count(*) from child where
  active` → `18`, but only 16 children exist on disk. The extra two are `Concurrent 1` and
  `Concurrent 2` in a bare `CONCURSEC` section, created 2026-09-20 05:26:04 by an **earlier version**
  of `test_two_classes_assembled_at_the_same_moment_both_finish`. The current test is correct — it
  uses a per-run `CONCURSEC-<hex>` section and deactivates it in a `finally`, and every one of the
  ~25 hex sections is `active = false`. The two orphans predate that design and the section-scoped
  cleanup can never match them. They sit in their own section, so they would never join a real class
  assembly. **Not yet fixed: the one-line deactivation was refused by this session's sandbox**
  (`Modify Shared Resources`), and `psql` was blocked for the rest of the session afterwards.
  The fix, for a session that can write: `update child set active = false where section =
  'CONCURSEC' and active` → expect `UPDATE 2`, then `select count(*) from child where active` → `16`.
  The deeper cause is that `engine audit` has no invariant over the roster; one that refuses an
  active child in a section the roster does not know would have caught this the day it happened.
