-- An English sample question is stored whole, so the educator approving a level reads its questions on the skill's page
-- (goals/smp_skill_shows_its_samples.yaml). Nimish, 2026-10-23: "How will the educator approve without having sample
-- questions?"
--
-- `skill_level_sample` (the Maths table) holds one line of words per example: no passage, no options, no right answer,
-- no wrong answers. The English seed (supabase/seed/english/, PR #254, #272) has 2,499 samples, each with all of those,
-- and nothing could hold them. Four new tables, named as the seed names them:
--   passage               a text a child reads, once (253)
--   rubric                what a person reads an open answer against (7)
--   english_sample        one sample: its skill, level, kind and number, the question as printed, the right answer
--   english_sample_wrong  each likely wrong answer of a sample, and the named mistake it shows
-- Additive only: no existing table, column or row is changed. Each is filled by `engine load` from the seed and holds
-- no approval: approving a level stays where it is (`skill_level.confirmed_by`).
--
-- Written to run twice.

create table if not exists passage (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  grade       text not null,
  kind        text not null,                      -- story, information, poem, …: the seed's words
  title       text not null,
  text        text not null,
  facts       jsonb,                              -- the facts a passage states, each with its source
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists rubric (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,
  name         text not null,
  applies_to   text not null,                     -- the kinds and uses it is for, in words
  criteria     jsonb not null,                    -- [{code, name, levels: {<scale word>: <what it looks like>}}]
  scale        text[] not null,
  skill_codes  text[] not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists english_sample (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  skill_code     text not null,
  difficulty     text not null,
  question_type  text not null,
  ord            smallint not null check (ord between 1 and 3),  -- its number within its skill, level and kind
  ask            text not null,                   -- what the child is told to do
  passage_code   text,                            -- the text it is about, if any
  text           text,                            -- the sentence, word or line printed under the ask (gaps as ___)
  options        jsonb,                           -- as printed: a list, or {left, right} to match
  answer         jsonb not null,                  -- the right answer: words, a list, pairs, or groups
  accept         jsonb not null default '[]',     -- other answers taken as right
  rubric_code    text,                            -- for an open kind: what a person reads the answer against
  key_points     jsonb,                           -- for an open kind: what a right answer says
  must_contain   jsonb,
  not_words      jsonb,                           -- words shown on purpose that are not words
  worked_out     jsonb,                           -- the rule code works the right answer out again by (`check`)
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (tenant_id, skill_code, difficulty, question_type, ord),
  foreign key (tenant_id, skill_code, difficulty) references skill_level (tenant_id, skill_code, difficulty)
    on update cascade,
  foreign key (tenant_id, question_type) references question_type (tenant_id, code) on update cascade,
  foreign key (tenant_id, passage_code) references passage (tenant_id, code) on update cascade,
  foreign key (tenant_id, rubric_code) references rubric (tenant_id, code) on update cascade
);
create index if not exists english_sample_skill_idx on english_sample (tenant_id, skill_code);

create table if not exists english_sample_wrong (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  sample_id      uuid not null references english_sample (id) on delete cascade,
  answer         text not null,                   -- the wrong answer as a child would write it
  mistake_code   text not null,
  op             text not null default 'any',     -- English's mistakes are the same in every operation
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (sample_id, answer),
  foreign key (tenant_id, mistake_code, op) references misconception (tenant_id, code, op) on update cascade
);
create index if not exists english_sample_wrong_sample_idx on english_sample_wrong (sample_id);

-- The engine writes them; the website reads them.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert, update, delete on passage, rubric, english_sample, english_sample_wrong to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on passage, rubric, english_sample, english_sample_wrong to app_web;
  end if;
end $$;

select internal.apply_conventions();
