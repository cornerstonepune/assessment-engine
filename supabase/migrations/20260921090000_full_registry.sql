-- The whole skill map, not the maths slice of it.
--
-- Until now `skill` and `milestone` held only NUM (37 of 244 skills), because the seed file was
-- `registry-num.json` — the maths extract taken while Phase 0 was being built. The source map
-- (the Skill Map Review artifact, window.CSMAP, built 2026-09-15) also carries 13 other domains
-- and four kinds of material this schema had nowhere to put: the school's own learning
-- objectives, its activity plans with three-level mastery descriptors, its report-card lines,
-- and the trait/pillar framework. Loading a third of a map and calling the registry done is how
-- a later phase discovers its inputs were never there.
--
-- Nothing here is speculative shape: every column below is a field that exists, filled, on every
-- row of the source. Links are many-to-many because the source says so — one learning objective
-- commonly names several skills.

-- ------------------------------------------------------------------ domains

create table domain (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                        -- NUM, LIT, HIN, SEB …
  name        text not null,                        -- "Numeracy & Logic"
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

-- A screen may never show a child's parent "NUM.OPS.02"; it shows the domain's name. That is
-- why the names are rows and not a dictionary in TypeScript.

-- ------------------------------------------------------------------ richer skills

alter table skill
  add column skill_type   text,                     -- academic | non_academic | trait_behaviour
  add column pillar       text,                     -- IND, … (the 7-pillar framework)
  add column ncf          text,                     -- NCF curricular area, as issued
  add column cg           text,                     -- NCF curricular goal, as issued
  add column authored_by  text;                     -- how the skill entered the map

-- `skill_type` is load-bearing, not decoration: a `trait_behaviour` or `non_academic` skill must
-- never be handed to the question bank and auto-marked. The council review (design/
-- skill-map-council-review.md, item 9) is explicit that putting a score on honesty is the kind
-- of measurement the school's founding principle rejects.

-- ------------------------------------------------------------------ learning objectives

create table learning_objective (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                        -- LO-G1-0008
  band        text not null,                        -- G1 …
  subject     text not null,                        -- "Numeracy"
  unit        text not null,                        -- "Addition & Subtraction"
  title       text not null,                        -- "Subtraction facts within 20"
  signal      text not null,                        -- Foundational|Conceptual|Procedural|Application|Stretch
  confidence  text not null default '',             -- how firmly the source mapped it
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table learning_objective_skill (
  tenant_id   uuid not null references tenant(id) on delete cascade,
  lo_code     text not null,
  skill_code  text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (tenant_id, lo_code, skill_code),
  foreign key (tenant_id, lo_code) references learning_objective (tenant_id, code) on delete cascade,
  foreign key (tenant_id, skill_code) references skill (tenant_id, code) on delete cascade
);
create index lo_skill_by_skill_idx on learning_objective_skill (tenant_id, skill_code);

-- `signal` here uses the same five words an item's signal does, because it came from the same
-- planning sheets. A skill set's `learning_objective` is prose typed by hand today; these are the
-- school's own, and a later chunk should point at them instead of paraphrasing them.

-- ------------------------------------------------------------------ activities

create table activity (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,                       -- ACT-K2-0085
  band         text not null,
  strand       text not null,                       -- "Maths" (the planning sheet's own word)
  name         text not null,
  objective    text not null default '',            -- the activity's stated learning objective
  level_1      text not null default '',            -- the school's own three-level mastery ladder
  level_2      text not null default '',
  level_3      text not null default '',
  confidence   text not null default '',
  requirement  text not null default '',            -- full | partial …
  printable    text not null default '',
  note         text not null default '',
  source_file  text not null default '',
  source_tab   text not null default '',
  source_row   text not null default '',
  source_url   text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

create table activity_skill (
  tenant_id      uuid not null references tenant(id) on delete cascade,
  activity_code  text not null,
  skill_code     text not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  primary key (tenant_id, activity_code, skill_code),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code) on delete cascade,
  foreign key (tenant_id, skill_code) references skill (tenant_id, code) on delete cascade
);
create index activity_skill_by_skill_idx on activity_skill (tenant_id, skill_code);

-- level_1/2/3 are the school's existing words for what partial and full mastery look like on a
-- real activity. They are the only three-level difficulty language in the whole map that was
-- written by teachers rather than derived by code — the non-maths answer to "what makes this
-- harder" starts here rather than from scratch.

-- ------------------------------------------------------------------ report items and traits

create table report_item (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  skill_code  text not null,
  band        text not null,
  title       text not null,                        -- the line as it appears on the report card
  section     text not null default '',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, skill_code, band, title),
  foreign key (tenant_id, skill_code) references skill (tenant_id, code) on delete cascade
);

create table trait (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,                       -- IND …
  band         text not null,
  label        text not null,                       -- "Independent & Disciplined"
  positive     text not null default '',            -- observed instances that count for it
  concern      text not null default '',            -- observed instances that count against
  expected     text not null default '',
  exceeding    text not null default '',
  linked       text not null default '',
  authored_by  text not null default '',
  source       text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code, band)
);

select internal.apply_conventions();
