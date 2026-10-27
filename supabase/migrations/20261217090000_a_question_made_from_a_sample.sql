-- Questions made from an educator's sample (goals/gen_from_a_sample.yaml). Nimish, 2026-10-26: "The capability to edit
-- a certain level in a skill by putting in the sample questions, and the ability for the system to then generate a
-- certain number of questions of that pattern."
--
--   english_sample_edit.made_from    the number of the sample a question was made from (none: a person wrote it)
--   english_sample_edit.flow_run_id  the model's run that wrote it (`flow_run`: model, cost, when)
--   english_sample_now               as before, with `made_from` last, so the page says "made from your sample"
--   maths_sample                     a Maths sample an educator put in, the case of its level code measured it as, and the
--                                    questions code made of it (none when it is no case the level's generator holds);
--                                    never changed
-- An English question made from a sample is a sample like any other once it passes the checks (english_check.py): a
-- draft, its level waiting for approval, removable one by one. A Maths question is made by code (ADR 0005), into
-- `item`; the sample's row lists them. Additive: two nullable columns, one table, one view gaining a column.
--
-- Written to run twice.

alter table english_sample_edit add column if not exists made_from smallint check (made_from >= 1);
alter table english_sample_edit add column if not exists flow_run_id uuid references flow_run(id);

create or replace view english_sample_now with (security_invoker = true) as
with last as not materialized (
  select distinct on (x.tenant_id, x.skill_code, x.difficulty, x.question_type, x.ord) x.*,
         count(*) over (partition by x.tenant_id, x.skill_code, x.difficulty, x.question_type, x.ord) - 1 as earlier
  from english_sample_edit x
  order by x.tenant_id, x.skill_code, x.difficulty, x.question_type, x.ord, x.created_at desc, x.id desc
)
select e.tenant_id, e.skill_code, e.difficulty, e.question_type, e.ord, e.ask, e.passage_code, e.text, e.options,
       e.answer, e.accept, e.rubric_code, e.key_points, e.not_words,
       coalesce((select jsonb_agg(jsonb_build_object('answer', w.answer, 'mistake_code', w.mistake_code)
                                  order by w.answer)
                 from english_sample_wrong w where w.sample_id = e.id), '[]'::jsonb) as wrong,
       null::text as edited_by, null::timestamptz as edited_at, 0::bigint as earlier, null::smallint as made_from
from english_sample e
where not exists (select 1 from english_sample_edit l where l.tenant_id = e.tenant_id and l.skill_code = e.skill_code
                    and l.difficulty = e.difficulty and l.question_type = e.question_type and l.ord = e.ord)
union all
select l.tenant_id, l.skill_code, l.difficulty, l.question_type, l.ord, l.sample ->> 'ask', l.sample ->> 'passage_code',
       l.sample ->> 'text', nullif(l.sample -> 'options', 'null'::jsonb), l.sample -> 'answer',
       coalesce(nullif(l.sample -> 'accept', 'null'::jsonb), '[]'::jsonb), l.sample ->> 'rubric_code',
       nullif(l.sample -> 'key_points', 'null'::jsonb), nullif(l.sample -> 'not_words', 'null'::jsonb),
       coalesce(nullif(l.sample -> 'wrong', 'null'::jsonb), '[]'::jsonb), l.edited_by, l.created_at, l.earlier,
       l.made_from
from last l
where not l.removed;

create table if not exists maths_sample (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  skill_code   text not null,
  difficulty   text not null,
  text         text not null check (btrim(text) <> ''),  -- as the educator typed it
  layout       text not null check (layout in ('line', 'columns')),
  cases        text[] not null default '{}',              -- the level's cases code measured it as; none: kept only
  item_ids     uuid[] not null default '{}',              -- the questions code made of it
  given_by     text not null check (btrim(given_by) <> ''),
  created_at   timestamptz not null default clock_timestamp(),
  updated_at   timestamptz not null default now()
);
create index if not exists maths_sample_level_idx on maths_sample (tenant_id, skill_code, difficulty, created_at);

drop trigger if exists maths_sample_kept on maths_sample;
create trigger maths_sample_kept before update or delete on maths_sample
  for each statement execute function internal.forbid_change();

-- The engine writes; the website reads.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on maths_sample to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on maths_sample to app_web;
  end if;
end $$;

select internal.apply_conventions();
