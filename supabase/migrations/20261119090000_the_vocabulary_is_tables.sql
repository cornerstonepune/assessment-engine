-- The school's words are tables, and every link to them a key (goals/b0a-the-vocabulary-is-tables.yaml, ADR 0084).
--
-- Nimish, 2026-10-20: "we need proper tables". A grade had no table; the four levels and the six states of a child's
-- map were lists of allowed words in CHECKs, and in code; a topic's subject and a skill's topic were codes the database
-- never checked. Now each word is a row with its order, and each link a key on (school, code), so adding a grade, a
-- level or a state is an insert. Nothing reads the new tables yet (B0b–B0d), so no paper, map or page changes.
--
-- The rows are supabase/seed/vocabulary.json's, made here for every school already there because a key needs them
-- before any load runs; a load keeps them (engine/core/vocabulary.py), and tests/test_vocabulary.py runs this file for
-- a new school and compares it with the seed. Written to run twice.

create table if not exists grade (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                         -- PG, N, K1, K2, G1 … G10
  name        text not null,                         -- "Nursery", "Grade 1"
  ord         int not null,                          -- grades sort by this, never by their code as text
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists difficulty (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                         -- Easy, Medium, Hard, Advance: the school's own words
  ord         int not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists child_state (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                         -- the graph's state (rebuild_child_skill_state)
  ord         int not null,                          -- weakest first
  words       text not null,                         -- what a page says for it
  colour      text not null,                         -- red, amber, green or grey on the website
  needs_work  boolean not null,                      -- a next paper works on a skill in this state
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

insert into grade (tenant_id, code, name, ord)
select t.id, v.code, v.name, v.ord
from tenant t cross join (values
  ('PG', 'PG', 0), ('N', 'Nursery', 1), ('K1', 'K1', 2), ('K2', 'K2', 3),
  ('G1', 'Grade 1', 4), ('G2', 'Grade 2', 5), ('G3', 'Grade 3', 6), ('G4', 'Grade 4', 7), ('G5', 'Grade 5', 8),
  ('G6', 'Grade 6', 9), ('G7', 'Grade 7', 10), ('G8', 'Grade 8', 11), ('G9', 'Grade 9', 12), ('G10', 'Grade 10', 13)
) v (code, name, ord)
on conflict (tenant_id, code) do nothing;

insert into difficulty (tenant_id, code, ord)
select t.id, v.code, v.ord
from tenant t cross join (values ('Easy', 0), ('Medium', 1), ('Hard', 2), ('Advance', 3)) v (code, ord)
on conflict (tenant_id, code) do nothing;

insert into child_state (tenant_id, code, ord, words, colour, needs_work)
select t.id, v.code, v.ord, v.words, v.colour, v.needs_work
from tenant t cross join (values
  ('patterned_error', 0, 'repeating mistake', 'red', true),
  ('emerging', 1, 'under half right', 'red', true),
  ('practising', 2, 'practising', 'amber', true),
  ('secure', 3, 'secure', 'green', false),
  ('stretch_ready', 4, 'ready to move up', 'green', false),
  ('not_enough_yet', 5, 'not enough yet', 'grey', false)
) v (code, ord, words, colour, needs_work)
on conflict (tenant_id, code) do nothing;

-- A topic's subject and a skill's topic: codes until now, keys from here.
alter table topic drop constraint if exists topic_tenant_id_subject_code_fkey;
alter table topic add constraint topic_tenant_id_subject_code_fkey
  foreign key (tenant_id, subject_code) references subject (tenant_id, code);
alter table skill_set drop constraint if exists skill_set_tenant_id_topic_code_fkey;
alter table skill_set add constraint skill_set_tenant_id_topic_code_fkey
  foreign key (tenant_id, topic_code) references topic (tenant_id, code);

-- A level: each list of the four words becomes a key into the table that holds them.
alter table item drop constraint if exists item_difficulty_check;
alter table item drop constraint if exists item_tenant_id_difficulty_fkey;
alter table item add constraint item_tenant_id_difficulty_fkey
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code);
alter table prescription drop constraint if exists prescription_difficulty_check;
alter table prescription drop constraint if exists prescription_tenant_id_difficulty_fkey;
alter table prescription add constraint prescription_tenant_id_difficulty_fkey
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code);
alter table sheet_template drop constraint if exists sheet_template_difficulty_check;
alter table sheet_template drop constraint if exists sheet_template_tenant_id_difficulty_fkey;
alter table sheet_template add constraint sheet_template_tenant_id_difficulty_fkey
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code);
alter table item_review drop constraint if exists item_review_difficulty_check;
alter table item_review drop constraint if exists item_review_tenant_id_difficulty_fkey;
alter table item_review add constraint item_review_tenant_id_difficulty_fkey
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code);

-- A child's state on a skill: the graph's six words, a key now.
alter table child_skill_state drop constraint if exists child_skill_state_state_check;
alter table child_skill_state drop constraint if exists child_skill_state_tenant_id_state_fkey;
alter table child_skill_state add constraint child_skill_state_tenant_id_state_fkey
  foreign key (tenant_id, state) references child_state (tenant_id, code);

select internal.apply_conventions();
