# Cornerstone Learning OS — platform architecture v1.1 (16 Sep 2026)

Status: draft for Aseem + Akanksha. Readable page: claude.ai/artifact/7e8BXcXXUfVaVMNjEr34UU (use that, not this file, to read).

**Supersedes** as the single build reference: `design/learning-os-design-v0.1.md`, `design/teacher-operating-system-proposal.md`, `design/child-graph-architecture.md`, `design/assessment-engine-spec-v0.1.md`, `design/tutor-engine-assessment.md`. Those remain as background; the sixteen open decisions across them are not re-listed here.

## 1. The problem

Every tool built so far carries its own private copy of the curriculum (the Skill Map page embeds a 2.9 MB snapshot). Views should be disposable and data singular; today it is inverted, so every view forks the data. Proof this week: the Hindi rebuild was patched into compiled `skills.csv`, so `registry_build/skills_def.py` and `mapping_def.py` are now out of sync with the data they generate. The pipeline built to prevent drift drifted in one week with one careful operator.

**Reversed decision.** All three prior docs said "Sheets as the store, database when a second class joins." Right for the teacher capture surface (voice, WhatsApp, paper stay), wrong for the system of record. The registry has ~6,600 cross-reference rows; "one ID, everything points at it" is a referential-integrity claim Sheets cannot enforce.

Holds today: 244 skills · 849 milestones · 1,750 objectives (G1–G4 only) · 2,216 activities (PG–K2 only) · 885 report lines (PG–G3, no G4 form) · 56 trait rows. The pre-primary/primary asymmetry is how the school plans, not a gap.

## 2. The shape: one database, many organs, agents for the flows

- **One bloodstream** — a single Postgres every part reads and writes. Not one giant program; not twenty services with twenty databases. "How is this child doing?" is a join across evidence × registry × roster; you cannot join across three databases.
- **Many organs** — separable parts with hard boundaries, own tables, published interfaces (exposed as tools agents can call). Any organ can be lifted into its own process later with no data migration.
- **Nervous system** — agents (Claude Agent SDK) with a goal, tools and a versioned prompt, orchestrated by a workflow runner. Every flow pauses for a human before anything irreversible.
- **Long-term reasoning**: flexibility comes from a correct data model and enforced seams, not from process topology. Multi-school is a schema decision — `tenant_id` on every table + RLS from day zero.
- **Pre-decided extraction trigger**: a second school with different residency rules, or 3+ concurrent developers.
- **Stack**: Next.js + TypeScript + Supabase Postgres, Mumbai `ap-south-1` (verified available) + Claude Agent SDK. Supabase's grain is TS; one toolchain; organs expose tools; server-rendered pages survive flaky 4G. Python only later, as one worker, if knowledge-tracing earns its place.

## 3. Four rings (cut by write-ownership, not nouns)

| Ring | Contains | Rule |
|---|---|---|
| A — source of truth | registry, roster, planning, evidence | Append/approve only; each exposes abilities as agent tools |
| B — derived | graph, coverage, report_draft | TRUNCATE-able any time; pure function of A; graph rebuilt nightly, never incremental |
| C — adapters | asr, llm, whatsapp, kriyo, fet, storage | One file each behind an interface; where "swappable" lives |
| D — flows (agents) | evening-extract, tomorrow-plan, fortnight-draft, worksheet-set, parent-brief, saturday-agenda | Goal + tools + versioned prompt; human confirm before write |

**Agents where judgment is needed, code where correctness is needed.** Agent: voice extraction, plan drafting, report pre-fill. Code: arithmetic item generation, closed-item marking, graph rebuild. Code-first-agent-fallback: name resolution.

Four easily-missed organs: `confirm` (one approval queue reused by every flow — built in Phase 1), `identity` (name/alias resolution with its own eval set; collision list generated from roster), `pii` (names/audio/photos in a separate schema, role and retention job), `concern` (safeguarding: a same-day flag goes **synchronously** to coordinator + head, bypassing confirm and the nightly batch; lives in `pii` with its own role and a timestamped escalation ladder teacher → coordinator → head → parent/external; never an evidence row, never visible to a parent lens).

**Roles inside the school** (RLS policies written before Phase 2 ships a name): lead teacher = own classes/current term, own queue, own practice notes; assistant educator (Didi) = own classes, records under own name; coordinator = all classes, queue health, coverage, concerns, practice notes for coaching; founder/head = + registry approvals + access audit; parent = own children, confirmed evidence only, via report/parent-brief output, never raw rows or comparisons. Plus an `access_log` (who *read* which child's sensitive records) and every agent tool call runs as the acting user's credentials, never a service account.

## 4. Nothing is hard-coded

Every structural fact is a table row, never a list in code. Current `build.py` has `BANDS = ['PG',…,'G4']` hard-coded — the exact thing this forbids.

| Fact | Table | Adding one = |
|---|---|---|
| Bands/grades | `band` (ordinal) | one row |
| Subjects, strands, domains | `subject`/`strand`/`domain` + alias tables | rows |
| Rating scales | `level_set`, `level` | rows; graph never compares across sets |
| Pillars/observables | `trait` | rows |
| Report form per band | `report_form`, `report_item` | rows; "no form for band" is a normal state |
| External frameworks (NCF, CBSE, Cambridge) | `framework` + `association(exactMatchOf)` | import + mapping rows, no migration |
| Prompts | `prompt` (versioned) | new version row, fetched by ID at runtime |
| Flows | workflow runner, not app code | trigger + prompt + tool list |
| Teacher↔class↔term | `assignment(valid_from, valid_to)` | dated rows |

**Test before Phase 0 ships**: add a fake Grade 5 with two subjects and one skill using only the loader and editing screens. Any code change needed = design failed.

## 5. Data model

**Registry — after 1EdTech CASE 1.1** (identity + associations; run none of its software):

```
node(id, tenant_id, node_type, uri, status)
node_code(code, node_id, valid_from, valid_to)      -- HIN.VARN.01 with history; old codes resolve
skill / milestone / objective / activity / report_item / trait   -- typed tables
subject, subject_alias, strand, strand_alias, unit(UNIQUE grade_band, subject, name)
level_set, level
association(src, dst, dst_type, assoc_type, weight, confidence, note, created_by, first_version_id)
   -- isChildOf | isPartOf | precedes | isRelatedTo | exactMatchOf | isTranslationOf
node_closure(ancestor, descendant, depth, path_kind)  -- materialised, rebuilt on publish
```

Deliberately not pure CASE: typed tables + one association table, so "all G2 Hindi objectives" is one indexed join.

**Evidence — after xAPI (IEEE 9274.1.1-2023)**:

```
evidence_event(id, tenant_id, child_id, skill_node_id, level_id, correct, polarity, channel,
               observed_at, stored_at, authority_id, state, confirmed_by, confirmed_at,
               superseded_by, registry_version_id, context jsonb, raw_ref)
```

`observed_at` vs `stored_at` vs `authority` is the key borrow (notes transcribed hours after the lesson). `state ∈ candidate|confirmed|superseded`; **graph reads only confirmed**.

**Evidence beyond a level (Ring A, Phase 3 — the level-per-skill model is right for G1–G4 and wrong for ages 2–6):** `artefact` (photo/audio/work sample linked to child+skill+event; Learning Stories assemble from these) · `work_cycle` (material, start, duration, repetitions, interrupted?, independent? — what a Montessori observation actually contains) · `trait_episode` (context, what happened, observer — pillars are frequency-across-contexts, never a heatmap, parents see stories only) · `evidence_event.language` + `child.home_languages[]` (graph unions `isTranslationOf` skills into one competence per language) · `support_plan` (child, targets, adjusted expectations, valid dates — graph compares against the plan when one exists) · `child_reflection` (child's own words, G1–G4).

**Rules that keep the graph honest** (thresholds in a table, not code): no level below a minimum (default ≥3 events from ≥2 observers/contexts — show "not enough yet"); every cell shows n-events / n-observers / last-seen; disagreement between adults = `contested` state, never averaged; recency weighting; at April handover prior-year estimates become "prior" with a 4-week fresh-eyes window; a Saturday observer-bias report per teacher (evidence by child, polarity balance, children seen by only one adult, gaps by home language).

**Versioning — snapshot per publication**: `registry_change` (proposed→approved) + `registry_version(snapshot jsonb, change_ids[])`. Registry <10 MB; 50 publications/yr ≈ 250 MB. Evidence stamps a ratified publication. Exceptions: enrolment and teacher assignment use `valid_from/valid_to`.

## 6. Compose, don't build (researched 15–16 Sep against live sources)

- **Plug in**: FET (AGPLv3 timetabler, v7.10.5 released 11 Sep 2026, XML in/out); Sarvam `saaras:v4` (keyterms biasing ≤50 terms, ₹30/hr, India-hosted, best independent Hindi 5.0% / Marathi 9.4% WER on Voice of India, IIT Madras, May 2026); Claude Agent SDK; WhatsApp Cloud API; Kriyo by export.
- **Copy schema only**: CASE 1.1; xAPI (Yet Analytics SQL LRS is the only maintained OSS LRS — skip); OneRoster academicSession nesting; Canvas Outcomes API; Moodle `core_competency`; Tapestry's custom-framework CSV shape.
- **Write off**: all Indian school ERPs (Teachmint, LEAD, Extramarks, MyClassboard, Entab, Campus 365 — no public APIs, no competency model); consumer observation apps (Seesaw, ClassDojo, Storypark, Kinderpedia — no API); enterprise curriculum mapping (Atlas/Rubicon, ManageBac, Chalk); Caliper, LTI, CLR/Open Badges; OpenSALT; Learning Locker; Fedena; Open edX.
- **Open**: Kriyo has no public developer docs — ask account manager for export + read API. Treat as reconciliation (`external_ref` table with match review), never overwrite-on-import.

## 7. The voice flow (the `evening-extract` agent)

1. Teacher records (WhatsApp or one-button page).
2. Context pack first: teacher → timetable → classes → rosters → aliases. Required input. The timetable is not the day: `day_override` (substitutions, assemblies, half-days, field trips, exam weeks) is read first; one-tap "I covered 3B today". Both adults in a room (lead + Didi) record under their own names. Attendance has a manual fallback (Kriyo has no API).
3. ASR: Sarvam saaras:v4 codemix, class roster as keyterms (≤50 → per class). Behind adapter.
4. Name reconciliation, code first: exact → alias table → Indic rules (-nsh↔-nch, sh↔ch, v↔w, ee↔i, a↔aa) → edit ≤2. Precomputed collision list; Ayan/Ayansh never auto-resolve. Absent child cannot receive an instance. Agent asks about the unresolved.
5. Extraction into four separately-routed streams: child evidence / teacher practice / logistics (HR) / affect.
6. Confirm queue <2 min, unmentioned children highlighted. Server-rendered, idempotent POSTs. Per-row save; unconfirmed after 48 h moves to coordinator view; WhatsApp reply-to-confirm; same child + same skill from two adults shown side by side.
7. Confirmed rows written (`observed_at` = session, `stored_at` = now). Every confirmation writes back to the alias table — and returns a 5-line "what the system now knows about your class this week", because a teacher who sees nothing come back stops on day four.
   **One path that does not wait**: a detected safeguarding concern goes synchronously to coordinator + head into `concern`, before the queue, before the batch.
8. Nightly: graph rebuild, coverage, `tomorrow-plan` agent drafts.

## 8. Verified data cleanup at load

| Problem | Count | Handling |
|---|---|---|
| crosswalk glob patterns (`PLS.SELF.*`) | 65 | expand at load |
| crosswalk dangling refs (`ART.CLAY`, `ART.MUS.03 (Routine songs)`) | 69 | strip/resolve or reject with report |
| crosswalk non-ID tokens (`CL0 Not yet`) | 23 | route to level/notes |
| unit names spanning >1 (grade, subject) | 164 of 415 | `UNIQUE(grade_band, subject, name)` |
| dirty subjects (Literacy / Literacy - English / Phonics) | 12 raw | alias table |
| dirty strands | 31 → ~15 | alias table |
| three incomparable milestone scales | 354 / 254 / 241 | every estimate declares level_set; never average across |
| activities without rubric | 989 of 2,216 | nullable rubric |
| skills with no objective and no activity | 28 | ship as Phase 0 coverage report (7 new Hindi drafts, 7 MOT.FIT) |

`teachable_unit` abstracts activity (PG–K2) vs lesson-against-objectives (G1–G4) so planning doesn't fork.

## 9. Council review (v1 → v1.1)

Three independent seats — teacher operations, child development, systems — each asked only for what was missing. Three gaps found by all three: no safeguarding path; no roles inside the school; one adult per class. Also added: evidence beyond a level (child dev); graph guards (child dev); `day_override` and a realistic confirm queue (teacher ops); coordinator adoption view moved to Phase 3 (teacher ops); PITR + rehearsed restore, private media bucket with signed URLs/size caps/retention job, `flow_run` table with dead-man check and one alert channel, job-health page in Phase 0 (systems); export job from Phase 1 (systems); WhatsApp Business verification started in Phase 2 (systems); Kriyo stays the parent channel until Phase 7 (teacher ops). Noted, not adopted yet: parents as an observation channel (Phase 7 decision); a hard 3-events/2-observers rule (it's a table threshold, not code).

## 10. Phases (~25–33 focused weeks; 6–9 months calendar)

| # | Ships | User | Child data | Effort |
|---|---|---|---|---|
| 0 | Postgres + idempotent loader + closure + four lenses (grade/skill/pillar/search) + orphan report + fake-G5 test + job-health page | Akanksha, Maya, teachers | none | 2–3 wk |
| 1 | Registry editing via `confirm` → publish + snapshot; export job | Maya proposes | none | 2 wk |
| 2 | Roster, enrolment (both adults per class), `day_override`, Kriyo reconciliation, FET, context packs, role policies, WhatsApp verification started, workflow runner + agent scaffold | Maya | names | 2–3 wk |
| 3 | `evening-extract` agent, one teacher one class, eval harness from day one; artefacts + work cycles; `concern` path; coordinator adoption view; media bucket + retention; PITR + rehearsed restore | 1 teacher | yes | 4–6 wk |
| 4 | Graph v0: heatmap, not-secure-at-band, unobserved-4-weeks | teacher + coord | yes | 3 wk |
| 5 | Planning + coverage + `tomorrow-plan` / `fortnight-draft` agents | teachers | yes | 3 wk |
| 6 | Assessment engine (code for correctness, agent for contexts/review) | Aseem, G1–G2 Maths | yes | 6–9 wk |
| 7 | Reports, Learning Stories from artefacts, handover with prior/current split, parent view via Kriyo (`parent-brief`); parents-as-channel decided | all | yes | 3–4 wk |

DB becomes source of truth at end of Phase 1 (loader re-runnable until then). Job queue Postgres-backed (graphile-worker/river), not Redis.

## 11. Verification

Loader idempotence (zero diff on re-run; exact row counts; zero dangling refs post-expansion). Playwright screenshot per lens at desktop + 400px. Deep links resolve on cold load incl. retired codes. Versioning: evidence written before a publish still resolves the old descriptor. Graph: TRUNCATE + rebuild byte-identical. Fake-Grade-5 test. **Eval harness from Phase 3 day one**: `gold` table + CLI scoring ASR WER, name-resolution P/R, extraction F1 on every prompt change.

## 12. Not certain

Running cost (Supabase Pro + PITR, media, Sarvam ₹30/hr × recording teachers, Claude tokens per flow logged in `flow_run`, hosting — a budget line belongs on the job-health page); all effort estimates (Phase 6 especially); Kriyo export capability; classroom audio will underperform the benchmark (measure own WER week 1 of Phase 3); workflow runner choice (n8n = no-code editable but poor version control; Inngest/Trigger.dev = code but versioned) — Phase 2 decision, reversible.

**The real risk is not architecture.** Sixteen open decisions across five docs are unanswered and nobody at the school has reviewed the Skill Map. Phase 1 moves the review into the tool so it stops depending on copy-paste.
