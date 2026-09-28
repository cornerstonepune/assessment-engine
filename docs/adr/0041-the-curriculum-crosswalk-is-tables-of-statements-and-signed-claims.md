# 0041 — The curriculum crosswalk is tables: what others say verbatim, what we say, and claims a person signs

Date: 2026-09-28
Goal: goals/crosswalk-start.yaml
The build started from the documents in hand (decision 5); `goals/crosswalk-signed.yaml` follows when the tables
are migrated, when BUILD-ORDER reaches them or Nimish moves them up.
Status: **proposed**. Nimish settled four of the five decisions on 28 Sep, and the rubric scale is recommended below
for his yes (see the end).
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

### Zone 2: age is the anchor, not the grade (decided 28 Sep)

Nimish, 28 Sep: "the ability of the child is the center. What should the child be able to do at what age should be our
baseline. At least till sixth standard, because our concept is towards fluid classrooms".

So every subject strand is a ladder of steps, each with the age a child is usually ready for it. Objectives and
official statements sit on those steps. A child's step in each strand comes from their evidence, not their grade, and
children on the same step can be taught together across grades. The grade stays as the class a child belongs to.

The frameworks' own levels carry the ages each framework prints: NCF-SE's stages by age, and Cambridge Primary
"typically for learners aged 5 to 11" (Science 0097, page 5; English 0058, page 8). Comparing on age rather than on
grade numbers avoids an off-by-one error. Six stages over ages 5–11 put a six-year-old near Cambridge Stage 2, while
NCF-SE puts them in Grade 1. That per-stage figure is an inference: Cambridge prints the range, not an age per stage.

```sql
alter table framework_level add column age_from numeric, add column age_to numeric;   -- as the framework prints them

create table progression (                  -- one ladder per subject strand: Maths · Number, English · Reading
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null, subject text not null, strand text not null,
  primary key (tenant_id, code)
);
create table progression_step (             -- a step, and the age a child is usually ready for it
  tenant_id uuid not null references tenant(id) on delete cascade,
  progression_code text not null,
  ord int not null,
  code text not null,                       -- MATH.NUMBER.5
  age_from numeric not null,
  age_to numeric not null,
  claim_id uuid not null references claim(id),
  primary key (tenant_id, progression_code, code)
);
create table objective_step (               -- where an objective sits on its ladder (replaces the grade band as the anchor)
  tenant_id uuid not null references tenant(id) on delete cascade,
  lo_code text not null,
  progression_code text not null,
  step_code text not null,
  claim_id uuid not null references claim(id),
  primary key (tenant_id, lo_code)
);
```

Which Cambridge stage or NCF-SE level lines up with a step is worked out from the ages, not typed. Where the school
teaches something earlier or later than a framework's age, that is a signed `objective_step` claim. The engine's
maths rungs are already a ladder like this (R1–R14, X1, X2); the progression generalises them to every subject.

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

Every assertion is a claim: a link, a statement, an outcome, a rubric line, a step. A person or a prompt proposes it.
Only the subject's signatory decides it. A claim's state is its latest decision, and with no decision it stays
"proposed, not signed". To start, one signatory, Akanksha, signs for every subject (Nimish, 28 Sep); a subject gets its
own signatory by adding a row.

```sql
create table signatory (                    -- who may sign a subject's claims, and from when
  tenant_id uuid not null references tenant(id) on delete cascade,
  subject text not null,                    -- '*' for every subject
  educator uuid not null,                   -- auth.users; the name stays in pii
  valid_from date not null,
  valid_to date,
  primary key (tenant_id, subject, educator, valid_from)
);
-- claim_decision refuses a decided_by who is not the subject's signatory on decided_at (a trigger)
```

```sql
create table claim (                        -- append-only
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  kind text not null,                       -- alignment · lo_statement · lo_capability · progression_step · objective_step ·
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

create table exclusion (                    -- an official statement the school chooses not to teach, and why
  tenant_id uuid not null references tenant(id) on delete cascade,
  statement_id uuid not null references framework_statement(id),
  progression_code text not null,
  claim_id uuid not null references claim(id),   -- the why is the claim's rationale
  primary key (tenant_id, statement_id, progression_code)
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

create table skill_outcome (                -- the written outcome a rubric grades: one step of one strand (decided 28 Sep)
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  code text not null,                       -- MATH.NUMBER.5
  progression_code text not null,
  step_code text not null,
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
create table skill_set_objective (         -- which objectives a skill set's questions assess: how a question reaches
  tenant_id uuid not null references tenant(id) on delete cascade,   -- an objective, a step and a rubric
  skill_set_code text not null,             -- every item already names its skill set and difficulty (Easy … Advance)
  lo_code text not null,
  claim_id uuid not null references claim(id),
  primary key (tenant_id, skill_set_code, lo_code)
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
- **`child_step`**: a child's current step in each strand, rebuilt from their evidence. It sets fluid groups.
- **`level_group`**: the children on the same step of a strand, across grades: who can learn together.
- **`framework_gap`**: every official statement for the ages a step covers that no approved alignment or
  exclusion covers. "Which Cambridge objectives are we missing?" becomes a query.
- **`readiness`**: per strand and step, the share of objectives with an approved statement, signed alignments and a
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
5. **Age, not grade number, lines frameworks up.** Each framework level carries the ages it prints, and each step
   the age a child is usually ready for it. A departure from a framework's age is a signed claim.
6. **Complete means a command passes.** The goal for a strand passes only when:
   - every objective has an approved statement, and for NCF-SE and for Cambridge a signed alignment or a signed
     reason there is none at that age (NCF-SE's Preparatory Stage, for one, has no negative numbers);
   - every outcome has a signed descriptor at every level of its scale;
   - `framework_gap` is empty.

### How the missing link gets built

1. **Import Cambridge.** Bring in Cambridge Primary (Stages 1–6) and Lower Secondary (Stage 7), word for word, with
   fingerprints. Move NCF-SE and NCERT, already checked, into `framework_statement`.
2. **Draw each strand's steps with their ages, and sign them.**
3. **Align on the drafting method, and let a sample become the gold set.** Nobody at school writes (Nimish, 28 Sep:
   "You can't expect Akanksha or any teacher to be writing"). The method, one prompt with a fixed way of thinking, is
   what Nimish and Akanksha agree. Akanksha approves or corrects a drafted sample, and the approved sample is the gold
   set every later draft is scored against (CLAUDE.md rule 7).
4. **Draft, strand by strand, with those prompts.** For each objective, its alignments with a
   relation and a reason, and its combined statement. For each strand, the skill outcome and a descriptor at every
   level. All of it lands as proposed claims.
5. **Code checks what code can.** Every cited statement's ages overlap its step's. Every outcome has every level.
   Descriptors describe what a child does. There are no duplicates. The gaps are listed.
6. **Educators sign** on one review screen per objective card: approve, reject or revise.
7. **Stop at 100% before moving on.** A strand's goal must pass before the next one starts.

## Rejected

- **One edge table, as `spine.json` is today.** Its ends are not foreign keys, a link's kind is checked by nobody,
  and there is nowhere to sign.
- **Links as columns on the skill, as `skill.cg` is today.** "CG-3" names no stage and no subject, and a column holds
  one link where a skill serves several.
- **A rubric per objective.** Grades 1–4 have 1,750 objectives, about 2.3 per unit. Four levels each is 7,000
  descriptors, too fine to observe and too many to sign. Questions still report per objective: each item names its
  skill set and its difficulty (Easy, Medium, Hard, Advance), and `skill_set_objective` ties the skill set to its
  objectives. So an objective's evidence is counted by code, and the rubric judges the strand's step from it.
  Outcomes per step of a strand come to roughly 40–60 a year of age (an estimate, until the steps are drawn).
- **Grade as the anchor ("Grade n is Stage n").** Cambridge prints "typically for learners aged 5 to 11" over six
  stages, so matching on the grade number puts a child a stage behind their age. Fluid classrooms group by level
  in a subject, not by grade.
- **A draft becoming the school's word by being written down.** Drafts stay claims until a person signs them.

## Decisions, as of 28 Sep

1. **Cambridge files.** Official copies come from the Cambridge School Support Hub, which needs a school login;
   Akanksha is asking whether Cornerstone is a registered centre. Until then, the structure is built from copies of
   Cambridge's own publications found on other schools' sites (English 0058 v2.1, Science 0097 v1) and from the
   official PE framework (0069) in the school's Drive. Each copy is recorded as a third-party copy, with its address
   and fingerprint, and is compared with the official file when it arrives (Nimish: "let's not shy away from doing
   that").
2. **The rubric scale (recommended, for Nimish's yes).** Four levels inside the school, reported on the national
   card's three:

   | Level | Meaning | The engine's evidence | On the Holistic Progress Card |
   |---|---|---|---|
   | Beginning | does parts of the step with help | right at Easy | Beginner |
   | Developing | does it alone in simpler cases, with slips in harder ones | right at Medium | Proficient |
   | Secure | does what the step says, alone and consistently: the target, and the signal to move on | right at Hard | Advanced |
   | Extending | uses it in new problems, explains it, finds the mistake | right at Advance | Advanced |

   The reasons:
   - The national Holistic Progress Card (PARAKH/NCERT) uses "three performance level descriptors - Beginner,
     Proficient, and Advanced" (Middle Stage guide, page 9). On it, Proficient still means "requires some support",
     so the school avoids the word inside its own scale.
   - Guskey (Phi Delta Kappan, 2024, page 6): "optimal discrimination, validity, and reliability are obtained using
     grading scales with four to seven levels or categories".
   - Every question already carries one of four difficulties (Easy, Medium, Hard, Advance). The engine's suggested
     level is the hardest difficulty a child answers right, consistently, and the educator confirms it. The
     thresholds are rows in `threshold`, to be checked against real papers.
   - NCF-SE asks for descriptors of behaviour, and for a child's progress to be compared with their own earlier
     report, not with other children.
3. **Rubrics per step of a strand.** Decided. Questions keep reporting per objective.
4. **Signatory.** Akanksha, for every subject, to start.
5. **Build.** Start now, as data shaped exactly like these tables, from the documents in hand. The tables themselves
   (migrations) wait for their place in BUILD-ORDER.

## Amended by the build, 28 Sep

Building the tables from the documents in hand (`research/crosswalk_build.py`, `docs/crosswalk/tables/`) showed what
the design above left out. The tables are these, as amended:

```sql
alter table framework_document add column provenance text not null
  check (provenance in ('publisher', 'third_party_copy'));   -- a copy found elsewhere is marked, and compared later
alter table framework_level
  add column age_basis text not null,        -- 'printed', or how the ages were worked out
  add column quote text not null,            -- the framework's own words the ages rest on
  add column pdf_page int not null;
alter table framework_statement
  add column printed_code text,              -- as printed: C-1.1 (unique only within a stage), *3Rw.01
  add column items text[] not null default '{}',   -- a list printed under the statement ("Understand addition as:")
  drop constraint framework_statement_kind_check,
  add constraint framework_statement_kind_check check (kind in ('curricular_goal', 'competency', 'learning_outcome',
    'learning_objective', 'characteristic', 'note', 'strand', 'substrand'));
    -- characteristic: a way of working for all stages (Cambridge's Thinking and Working Mathematically);
    -- note: a printed line under a heading ("By end of Stage 4 learners should have a secure understanding of phonics.")
alter table progression add column cambridge_strands text[] not null default '{}';
alter table claim add column rule text,      -- or the code that proposed it (a step per year of age)
  drop constraint claim_check,
  add constraint claim_one_proposer check (num_nonnulls(proposed_by, prompt_purpose, rule) = 1);
alter table rubric_level
  add column suggested_by text not null,     -- the engine's evidence that suggests it: "right at Hard"
  add column reports_as text not null check (reports_as in ('Beginner', 'Proficient', 'Advanced'));

create table no_alignment (                  -- a signed reason a framework has nothing for an objective at its age
  tenant_id uuid not null references tenant(id) on delete cascade,
  lo_code text not null,
  framework_family text not null check (framework_family in ('NCF-SE', 'Cambridge')),
  claim_id uuid not null references claim(id),   -- the reason is the claim's rationale
  primary key (tenant_id, lo_code, framework_family)
);
create table gap_proposal (                  -- what to do with an official statement no objective covers
  tenant_id uuid not null references tenant(id) on delete cascade,
  statement_id uuid not null references framework_statement(id),
  step_code text not null,
  proposal text not null check (proposal in ('add_to', 'new')),   -- 'leave_out' is an exclusion
  lo_code text,                              -- add_to: the objective it joins
  what_we_say text,                          -- new: the new objective's sentence
  claim_id uuid not null references claim(id),
  primary key (tenant_id, statement_id, step_code)
);
-- view objective_waiting: the school's objectives with no objective_step yet, for the drafting method to place
```

This repository is public, and Cambridge permits "Registered centres … to copy material from this booklet for their own
internal use". So a Cambridge statement's words are not in git. The tracked row keeps its code, stage, strand, page
and `text_sha256`, a fingerprint of its words. The words are rebuilt into `data/` from the recorded copy by
`research/crosswalk_cambridge.py`, and the build refuses words whose fingerprint differs. In the database (not
public) `text` holds them. NCF-SE's and NCERT's words were already published in `docs/spine/sources/`.

In the research data a row names what it refers to by code (`framework_code` and `statement_code`, `outcome_code`)
where the database will hold ids, and the signatory is named; in the database she is her auth user id and her name
stays in `pii`.
