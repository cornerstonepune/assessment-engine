# 0039 — The curriculum crosswalk is tables: what others say verbatim, what we say, and claims a person signs

Date: 2026-09-28
Goal: none — a design, not yet built. `goals/crosswalk-signed.yaml` is written with the build, when BUILD-ORDER
reaches it or Nimish moves it up (decision 5 below).
Status: **proposed**. Five decisions are Nimish's (at the end).
Source: the schema it extends, `supabase/migrations/20260917090000_ring_a.sql` and `20260921090000_full_registry.sql`;
the spine it replaces as the record, `docs/spine/spine.json` (ADR 0037).

## Context

Nimish, 2026-09-28, on the spine page: "most of this is where you are saying that it's not been linked, so it is
incomplete, right? I mean, proposed link not signed. Ideally, it should still be at a subject level for a certain
learning objective: what does the NCF say, what does IGCSE say, and what are we going to say as a combination … That
essentially translates into the written skill outcome at a rubric level … for all the grades … think of this as a proper
backend architecture. If you have to convert this into a proper set of tables such that this mapping becomes accurate,
how will you want to do it? What will the tables look like?"

He is right that the chain is incomplete: it is complete in shape and unproven in content. On 28 Sep:

| Link | Today |
|---|---|
| NCF-SE statements (goals, competencies) | 814 imported, each found word for word on its page |
| NCERT outcomes, Classes 1–10 | 729 imported, each found word for word on its page |
| Cambridge (Primary, Lower Secondary) | none imported. The school's Drive holds one official framework, Primary Physical Education (0069, "Version 2", © UCLES 2019); Maths, English and Science are not there |
| The school's objectives | 1,750 for Grades 1–4 (`learning_objective`); none for Grades 5–7 |
| Objective → engine skill | 2,012 links, the school's own (`learning_objective_skill`) |
| Objective → NCF-SE statement | none. 981 links exist one level up, at the unit, all drafted by a subject reviewer, none signed |
| Objective → Cambridge statement | none |
| Skill → NCF-SE | a goal code on each of the 244 skills (`skill.cg`, e.g. "CG-3") that names no stage or subject, so it is ambiguous |
| "What we say", the school's combined statement | none. Objectives carry a short title ("Place value (reading/writing large numbers, partitioning, rounding)") |
| Written skill outcome with rubric levels | none. `milestone` holds one descriptor per skill per band and `trait` holds expected and exceeding lines, both drafts |
| Signatures | none. No table records who approved a link |

A link in `spine.json` is one row in a list of edges: two ids, a kind, and who made it. Nothing checks that its ends
exist in the database, and nothing records that a person agreed with it.

## Decision (proposed)

Five zones. Seven of the tables exist; the rest are new. Everything follows the constitution:
- structure is rows (rule 1);
- prompts are rows (rule 2);
- evidence is append-only (rule 4);
- migrations only (rule 9);
- `internal.apply_conventions()` turns on RLS for every table.

### Zone 1: what others say (imported word for word, never edited)

```sql
create table framework (                    -- NCF-SE 2023, NCERT LO 2017, Cambridge Primary Mathematics, the school's map
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null,                       -- NCF-SE-2023, NCERT-LO-2017, CAM-PRI-MATH
  name text not null,
  publisher text not null,                  -- NCERT · Cambridge International · the school
  kind text not null check (kind in ('national', 'international', 'school')),
  edition text not null,                    -- as printed: "First Edition, October 2024"
  unique (tenant_id, code)
);

create table framework_document (           -- the very copy the import read
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  framework_id uuid not null references framework(id),
  url text not null,
  sha256 text not null,                     -- a changed file is refused (docs/spine/sources/official_documents.json today)
  bytes bigint not null,
  reading text not null,                    -- how its text was taken out: "PyMuPDF 1.28.2, pages joined with \n"
  retrieved_at timestamptz not null,
  unique (framework_id, sha256)
);

create table framework_level (              -- the framework's own levels; a level can be a band:
                                            -- NCF-SE Preparatory is Grades 3-5, and Cambridge PE
                                            -- groups Stages 1-3 and 4-6 (codes like 123MW.01)
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  framework_id uuid not null references framework(id),
  code text not null,                       -- Preparatory · Class 3 · Stage 3
  ord int not null,
  unique (framework_id, code)
);

create table framework_statement (          -- append-only; a correction supersedes
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  framework_id uuid not null references framework(id),
  document_id uuid not null references framework_document(id),
  parent_id uuid references framework_statement(id),   -- goal → competency; strand → substrand → objective
  level_id uuid references framework_level(id),
  kind text not null check (kind in ('curricular_goal', 'competency', 'learning_outcome',
                                      'learning_objective', 'strand', 'substrand')),
  code text not null,                       -- CG-1 · C-1.1 · the Cambridge code as printed
  area text not null,                       -- the framework's own subject and strand names, as printed
  text text not null,                       -- word for word; research/spine_verify.py finds it on its page
  pdf_page int not null,
  printed_page int,
  supersedes_id uuid references framework_statement(id),
  unique (document_id, code)
);
-- trigger: before update or delete → internal.forbid_change()
```

### Zone 2: which grade reads which level (a school decision, signed)

```sql
create table grade_equivalence (            -- Grade 3 ↔ NCF-SE Preparatory ↔ NCERT Class 3 ↔ Cambridge Stage 3
  tenant_id uuid not null references tenant(id) on delete cascade,
  grade text not null,                      -- G1 … G7, the school's bands
  level_id uuid not null references framework_level(id),
  claim_id uuid not null references claim(id),
  primary key (tenant_id, grade, level_id)
);
```

### Zone 3: what we say

`learning_objective` exists (code `LO-G3-0930`, band, subject, unit, title, signal). It gains its teaching order.
The school's own statement is kept in versions:

```sql
alter table learning_objective add column ord int;   -- teaching order within a grade and subject

create table lo_statement (                 -- "what we say": NCF-SE and Cambridge combined, and further than both
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  lo_code text not null,
  text text not null,
  claim_id uuid not null references claim(id),
  supersedes_id uuid references lo_statement(id),
  foreign key (tenant_id, lo_code) references learning_objective (tenant_id, code)
);
```

### Zone 4: claims and signatures (the missing link)

Every assertion is a claim: a link, a statement, an outcome, a rubric line, a grade equivalence. A person or a prompt
proposes it. Only a person decides it. A claim's state is its latest decision, and with no decision it stays
"proposed, not signed".

```sql
create table claim (                        -- append-only
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  kind text not null,                       -- alignment · lo_statement · lo_capability · grade_equivalence ·
                                            -- skill_outcome · outcome_objective · rubric_descriptor · exclusion
  proposed_by uuid,                         -- an educator (auth.users); the name stays in pii
  prompt_purpose text,                      -- or the prompt that drafted it (CLAUDE.md rule 2)
  prompt_version int,
  rationale text not null,
  created_at timestamptz not null default now(),
  check ((proposed_by is null) <> (prompt_purpose is null)),
  foreign key (tenant_id, prompt_purpose, prompt_version) references prompt (tenant_id, purpose, version)
);

create table claim_decision (               -- append-only; decided by a person, never by a prompt
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  claim_id uuid not null references claim(id),
  decision text not null check (decision in ('approved', 'rejected', 'revised')),
  decided_by uuid not null,                 -- an educator
  decided_at timestamptz not null default now(),
  note text not null default ''
);

create table alignment (                    -- one school objective ↔ one official statement
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  lo_code text not null,
  statement_id uuid not null references framework_statement(id),
  relation text not null check (relation in ('meets', 'extends', 'partly_meets', 'prepares_for')),
  claim_id uuid not null references claim(id),
  unique (tenant_id, lo_code, statement_id),
  foreign key (tenant_id, lo_code) references learning_objective (tenant_id, code)
);

create table exclusion (                    -- an official statement the school chooses not to teach in a grade, and why
  tenant_id uuid not null references tenant(id) on delete cascade,
  statement_id uuid not null references framework_statement(id),
  grade text not null,
  claim_id uuid not null references claim(id),   -- the why is the claim's rationale
  primary key (tenant_id, statement_id, grade)
);

create table capability (                   -- the graduate profile's eight, and the word each mostly shows
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null, label text not null, text text not null,
  primary key (tenant_id, code)
);

create table lo_capability (                -- the "why": which capability an objective builds
  tenant_id uuid not null references tenant(id) on delete cascade,
  lo_code text not null,
  capability_code text not null,
  weight text not null check (weight in ('primary', 'secondary')),
  claim_id uuid not null references claim(id),
  primary key (tenant_id, lo_code, capability_code)
);
```

### Zone 5: how we'll know (the written outcome, its rubric, the evidence)

```sql
create table rubric_scale (                 -- the school's own levels, as rows (decision 2)
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null, name text not null,
  primary key (tenant_id, code)
);
create table rubric_level (
  tenant_id uuid not null references tenant(id) on delete cascade,
  scale_code text not null,
  ord int not null,
  code text not null,
  label text not null,
  meaning text not null,
  primary key (tenant_id, scale_code, code)
);

create table skill_outcome (                -- the written outcome a rubric grades: one strand of a subject in a grade
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null,                       -- MATH.G3.NUMBER
  subject text not null,
  grade text not null,
  text text not null,
  scale_code text not null,
  claim_id uuid not null references claim(id),
  supersedes_id uuid references skill_outcome(id)
);
create table outcome_objective (            -- the objectives an outcome gathers
  outcome_id uuid not null references skill_outcome(id),
  lo_code text not null,
  claim_id uuid not null references claim(id),
  primary key (outcome_id, lo_code)
);
create table outcome_skill (                -- the engine's skills and rungs whose worksheet evidence informs it
  outcome_id uuid not null references skill_outcome(id),
  skill_code text not null,
  rung_code text,
  primary key (outcome_id, skill_code)
);
create table rubric_descriptor (            -- what a child does at each level; one current, signed line per level
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  outcome_id uuid not null references skill_outcome(id),
  level_code text not null,
  text text not null,                       -- observable: what the child does, not what they "understand"
  exemplar text not null default '',
  claim_id uuid not null references claim(id),
  supersedes_id uuid references rubric_descriptor(id)
);

create table outcome_evidence (             -- append-only, like evidence_event (CLAUDE.md rule 4)
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  child_id uuid not null references child(id) on delete cascade,
  outcome_id uuid not null references skill_outcome(id),
  level_code text not null,
  source text not null check (source in ('worksheet', 'observation', 'project', 'portfolio')),
  evidence_event_id uuid references evidence_event(id),   -- when a worksheet item informs it
  observed_by uuid,                         -- when an educator saw it
  observed_at timestamptz not null,
  supersedes_id uuid references outcome_evidence(id)
);
```

### The answers, as views (Ring B: derived, rebuilt at any time)

- **`claim_state`**: each claim with its latest decision (proposed, approved, rejected or revised).
- **`lo_crosswalk`**: one row per objective, with:
  - what NCF-SE says, what Cambridge says and what NCERT says (approved alignments only);
  - what we say (the current approved statement);
  - the capability it builds;
  - its outcomes, and whether each rubric is complete.
  The spine page reads this view.
- **`framework_gap`**: every official statement at a level equivalent to a grade that no approved alignment or
  exclusion covers. "Which Cambridge objectives are we missing?" becomes a query.
- **`readiness`**: per grade and subject, the share of objectives with an approved statement, signed alignments and a
  complete rubric. This is the build's progress bar.
- **`child_outcome_state`**: a child's current level on each outcome, rebuilt by `engine graph` from
  `outcome_evidence`.

### What makes the mapping accurate

1. **Official text is never typed.** Statements come only from the importer, and the checker finds each one word for
   word on its page, in the copy whose fingerprint is recorded. A trigger refuses any edit.
2. **A model never signs.** A prompt may propose. `claim_decision.decided_by` is always a person.
3. **Unsigned is visible and counts for nothing.** The views read approved claims only. A proposal shows as proposed,
   as the spine page shows it today.
4. **Every end of every link exists.** Foreign keys replace today's edge list, whose ids only a script checked.
5. **Grade and stage are matched on purpose.** Grade 3 ↔ Cambridge Stage 3 is a signed row, not an assumption.
6. **Complete means a command passes.** The goal for a grade and subject passes only when:
   - every objective has an approved statement, a signed NCF-SE alignment, and a signed Cambridge alignment or a signed
     reason there is none;
   - every outcome has a signed descriptor at every level of its scale;
   - `framework_gap` is empty.

### How the missing link gets built

1. **Import Cambridge.** Bring in Cambridge Primary (Stages 1–6) and Lower Secondary (Stage 7), word for word, with
   fingerprints. Move NCF-SE and NCERT, already checked, into `framework_statement`.
2. **Sign the grade equivalences.**
3. **Write a small gold set by hand.** Educators write the alignments, statements, outcomes and rubrics for one grade
   and subject. The prompts are evaluated against it before they are used (CLAUDE.md rule 7).
4. **Draft, grade by grade and subject by subject, with those prompts.** For each objective, its alignments with a
   relation and a reason, and its combined statement. For each strand, the skill outcome and a descriptor at every
   level. All of it lands as proposed claims.
5. **Code checks what code can.** Every cited statement exists at an equivalent level. Every outcome has every level.
   Descriptors describe what a child does. There are no duplicates. The gaps are listed.
6. **Educators sign** on one review screen per objective card: approve, reject or revise.
7. **Stop at 100% before moving on.** The grade and subject's goal must pass before the next one starts.

## Rejected

- **One edge table, as `spine.json` is today.** Its ends are not foreign keys, a link's kind is checked by nobody,
  and there is nowhere to sign.
- **Links as columns on the skill, as `skill.cg` is today.** "CG-3" names no stage and no subject, and a column holds
  one link where a skill serves several.
- **A rubric per objective.** Grades 1–4 have 1,750 objectives, about 2.3 per unit. Four levels each is 7,000
  descriptors, too fine to observe and too many to sign. Outcomes per strand, each gathering its objectives, come to
  roughly 40–60 per grade (an estimate, until the strands are drawn).
- **A draft becoming the school's word by being written down.** Drafts stay claims until a person signs them.

## Decisions for Nimish

1. **Which Cambridge framework, and the files.** For Grades 1–7 it is Cambridge Primary (Stages 1–6) and Lower
   Secondary (Stages 7–9); IGCSE begins after Lower Secondary. The Drive has only Primary PE, so the Maths, English
   and Science frameworks must come from the school's Cambridge account. "IGCSE Curriculum.pdf" in the Drive is
   another school's Grade 1 map; the importer accepts only Cambridge's own publication. Which subjects, and is Grade n
   Stage n?
2. **One rubric scale.** The school uses several today:
   - the Hindi reading rubric: Beginning, Developing, Fluent, Expressive;
   - report cards: Outstanding, Desired, Improving, out of 10, where 6/10 appears under two labels;
   - planning sheets: Level 1, 2 and 3;
   - the registry: a score out of 10, and yes / sometimes / no.
   Which one grades the outcomes?
3. **Where rubrics sit.** Per strand and grade, gathering objectives (recommended), or per objective.
4. **Who signs each subject.**
5. **When to build.** BUILD-ORDER is on step 1 of ten, and ADR 0037 puts the spine's tables after the ten. The
   choice is to pilot now as data shaped like these tables (Grade 3 Maths, no migration), or to move the tables up.
