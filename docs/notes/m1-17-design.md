# M1-17 — a K2 child's plan and growth (design, draft; no code)

W3, gate N10 (the skill graph), reading side. Design only. Nimish's model (5 Nov): in K2 the rubrics are the
assessments; a level 0–3 on an activity is the observation on every skill the activity maps to.

## What I could not read

`cornerstonepune/teacher-os` was refused to this session, so these are **unread**: `blueprint/decisions.md` (D-007, D-019,
D-021, D-062, D-073–D-076), `child-and-learning.md` (§4 "ready next"), `observation-model.md`, the M1-17 card and
`blueprint/HANDOFF.md`. What follows is from this repo (migrations, engine, `docs/notes/m1-01…m1-04`, `m1-15`) and from
the orchestrator's addendum. Where a rule below comes only from the addendum or from a comment in a migration, it says so.
Anything marked *unverified* is a guess to be checked against the unread documents.

## The two outside repositories — method only, and how far I read

Read through a summarising fetch, not file by file. **I did not read their prompt or merge code**; the paths are as the
READMEs name them. *Unverified* beyond that.

- `withmarbleapp/os-taxonomy`: topics are nodes (`data/topics.json`: id, subject, age range, `evidence` criteria, an
  `assessmentPrompt`); dependencies are edges (`data/dependencies.json`: `hard`|`soft` and a written `reason`), a DAG;
  checked by `scripts/validate.mjs`. Licences: data ODbL, text CC BY-SA 4.0 (share-alike). Pipeline: not found.
- `haolpku/K12-KGraph`: `src/kg/run_pipeline.py`; 9 edge types incl. `prerequisites_for`; DAG validation; a
  book→subject→global merge (file not located). Licence: dataset CC BY-NC-SA 4.0 (**non-commercial**), code MIT.
- **What we take:** edges with a strength and a written reason; a DAG check; a person confirms. **We already have all
  three** (`skill_link`, M1-15). **We copy no data**: both licences would bind it.

## 1. A rubric level on an activity becomes observations on skills — already built

| Step | Where | State |
|---|---|---|
| Activity → skills | `activity_skill` (activity_code, skill_code) | exists |
| Educator's level 0–3 | `activity_observation.reached_level` (append-only; correction = new row, `supersedes`) | exists |
| One evidence row per skill, all sharing the observation id | `evidence_event` kind `observed`, `observation_id` (`w3_read/voice_confirm.py`) | exists |
| Per child + skill state | `child_observed_state` ← `graph_observed_states()` (M1-02), rule rows `observed_rule`/`observed_weight` | exists |
| Read calls | `POST /k2/picture`, `POST /k2/child` (`w3_read/k2_picture_reads.py`) | exists, **no screen reads them** |

Gaps, none needing a table:
- **Level is derived, not typed.** Today the educator says above/as expected/below against an *expected* level and the
  engine stores `reached_level` (`voice.outcome_moves_level`). Nimish's model has her give the rubric level itself. Simplest
  reading, recorded: **`reached_level` is the rubric level**; nothing else changes. If the form should take the level
  directly, that is a form change writing `reached_level` itself, not a schema change. *Unverified* against D-0xx.
- **`activity_skill` resolves to the broad skills, as evidence does.** Its `skill_code` has a foreign key to `registry_skill
  (tenant_id, skill_code)`, not to the maths micro-steps. Checked on live by the orchestrator, 5 Nov: 953 rows for 590 K2
  activities and 153 distinct skills, all `source = person` (the school's own links), none machine-made. So every K2 link
  resolves to a registry skill by the key itself. My first reading of the migrations was wrong; no count is needed.

## 2. Storage of progress: qualitative and quantitative together, K2 → later grades

No new store. The truth is already two append-only things plus one derived:
- **Numbers:** `evidence_event` (child, **registry skill**, observed_at, observation_id) + `activity_observation.reached_level`.
  A registry skill is not tied to a grade (it spans PG–K2), so a child who moves on keeps the same ledger; only the
  derived row carries `grade_code` (`child_observed_state` is unique on child+skill+grade). Growth that is "not linear" is
  therefore a read over the ledger by skill, never by grade.
- **Words:** `pii.educator_note` transcript, with the sentence guard of M1-03 (withheld if it may name a child; only the
  recording educator and coordinators see it). The note is joined **by `note_id` through the observation**, so a number and
  its sentence are always the same moment. Names never enter app tables (rule 6, D-021 per the addendum).
- **Derived (ring B):** `child_observed_state`, rebuildable.
- Later grades: the written path (`child_skill_state`, keyed by rung) and the observed path stay separate tables
  (M1-02's decision, to keep `engine past` equal). A page that must show both for one child reads both; I propose no merge.
- **Migration: none expected.** If the build finds one needed, it merges alone (orchestrator) and `rules.json` is updated.

## 3. Ready next — confirmed links only

For a child and skill S not yet secure-or-better: S is **ready** when *every* `skill_link_confirmed` row with
`skill_code = S` has its `before_code` in state `secure` or `secure_to_recheck`? — *unverified*: whether
`secure_to_recheck` counts is a school rule I cannot read; **proposed: secure only**, hard links all, soft links not required.
- A skill with **no confirmed link** is never "not ready" and never "ready": it is shown under *Seen* or *Not seen yet* with
  no claim. A prerequisite with no observation is *unknown*, not *missing*.
- Today `skill_link` holds **no rows** until a person loads a list (M1-15), so *Ready next* ships with a designed empty
  state: "No confirmed links yet." Reads go through `skill_link_confirmed` only (a repo test scans for the audit view).
- Computed on read in the engine (a few rows per child); not stored.

## 4. Growth — movement over time, a trend, not a score

Per child + skill, from the ledger of **named, individual, confirmed, non-superseded** observations (the same filters as
`CELLS_SQL`): `first_seen`, `last_seen`, `levels_by_month` (month → the highest level reached that month, and how many
days seen), and `trend ∈ {up, steady, down, too few}` comparing the latest two months seen. No number is summed or
averaged into a score. "The rest did as expected" shows no level (as in M1-03). A gap month is a gap, not a zero.
Thresholds (months compared, minimum days) are `threshold`/config rows. Pure function in `assess/`, SQL only for fetching.

## 5. Data shape each screen reads (engine → screen; Sr. No., never a name or id)

`POST /k2/child` gains (additive, existing keys unchanged):
`{class, roll_no, plan:[{skill:{code,name}, state:{code,words,icon}, level, last_seen, sentence, sentence_note}],
 ready_next:[{skill, because:[{before:{code,name}, strength, reason}]}], seen_nothing_yet:[skill],
 growth:[{skill, first_seen, last_seen, by_month:[{month, level, days}], trend}]}`.
`POST /k2/picture` unchanged in shape; the screen adds a per-skill summary strip (counts per state) from the cells.
Both stay 403 while `voice.screens_enabled` is off.

## Screens (after the reads)

Child page (plan, ready next, growth) and class picture, in the real app, behind the staff preview with the educator
switches off. The preview helper is being added by the '4b' session (`educator.preview_roles`); **I build against it and
write none**. Tokens only from `design-system/tokens.css` (`--surface` until the white ground lands) — *I have not read that
file yet*.

Colour rules that bite here:
- Seeded `child_state.colour` is `red` for `emerging`/`patterned_error`. D-075 (per the addendum) says terracotta is never
  on a child. **A screen must not use `child_state.colour` as is.** Proposed: render by state *word + icon* in olive/amber/
  monsoon only, and treat the seed's `red` as a defect to raise, not to fix in this task (it is a shared contract).
- "Not seen" is plain text and a grey outline, never an alarm or "not secure".
- The class picture is staff-only; no parent route.

## Build order (small draft PRs, tests first, each seen failing)

1. `assess/` growth + ready-next pure functions, with hand-worked tables. 2. Engine reads extended + route + contract
regeneration (`bin/engine contract`). 3. Child page. 4. Class picture. Each with a goal file (`engine goal`), the browser
test, taps counted, shots at 1280 and 390 px, token check. No model call anywhere in this task.

## Open questions for the orchestrator (answered 5 Nov: 1 secure only; 2 the screens map states to D-075 chips, the seed is left alone; 3 not needed, see section 1; 4 build as listed)

1. Does `secure_to_recheck` count as "done" for ready-next? (proposed: no)
2. Should the form take the rubric level directly? (proposed: yes later; not in this task)
3. The seeded red on child states: who changes it?
4. (answered 5 Nov: yes; see section 1)

## Verified

Nothing yet: design only. Facts above were read from the files named; none was run.
