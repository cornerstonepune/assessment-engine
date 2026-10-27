-- An educator stops a kind of question at a level, or across a skill, and can start it again
-- (goals/gen_retire_a_kind.yaml). Nimish, 2026-10-26: "the educator also, today, does not want certain types of
-- questions. They should be able to delete those kinds of questions from the bank itself."
--
-- Answers already given to a question must stay readable (rule 4), so "delete from the bank" is a stop, never a DELETE:
--   skill_level_kind_stop  one stop or restart of one kind at one level, who, when, and the papers it withdrew for
--                          approval again; never changed. The newest row for a level and kind says where it stands
--   kind_stopped           the kinds stopped now, one row per level and kind
--   drawable_item          what a paper may draw, as before, less a question whose kind is stopped at its level
-- A stop across a skill is a row for each level that asks the kind. Past papers keep their questions, and every
-- question keeps its row: only the next draw changes. The engine writes (engine/w1_bank/retire.py); the website reads.
--
-- Additive: no existing table, column or row is changed; `drawable_item` keeps its columns.
-- Written to run twice.

create table if not exists skill_level_kind_stop (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  skill_code     text not null,
  difficulty     text not null,
  question_type  text not null,
  stopped        boolean not null,             -- false: started again
  withdrawn      text[] not null default '{}', -- the codes of the approved papers not yet given it sent back for approval
  changed_by     text not null check (btrim(changed_by) <> ''),
  created_at     timestamptz not null default clock_timestamp(),  -- a stop and a restart in one sitting stay in order
  updated_at     timestamptz not null default now()
);
create index if not exists skill_level_kind_stop_idx
  on skill_level_kind_stop (tenant_id, skill_code, difficulty, question_type, created_at);

drop trigger if exists skill_level_kind_stop_kept on skill_level_kind_stop;
create trigger skill_level_kind_stop_kept before update or delete on skill_level_kind_stop
  for each statement execute function internal.forbid_change();

create or replace view kind_stopped with (security_invoker = true) as
select * from (
  select distinct on (tenant_id, skill_code, difficulty, question_type)
         tenant_id, skill_code, difficulty, question_type, stopped, changed_by, created_at
  from skill_level_kind_stop
  order by tenant_id, skill_code, difficulty, question_type, created_at desc, id desc
) last
where stopped;

-- The kind is worked out once per question (`offset 0` keeps it from being inlined into each test that reads it): the
-- same rows as before, in about a tenth of the time (57 ms against 606 ms for 28,700 questions, a fresh copy, 2026-10-26).
create or replace view drawable_item with (security_invoker = true) as
  select i.*, q.question_type
  from item i
  cross join lateral (select question_type_of(i.fmt, i.template) as question_type offset 0) q
  join skill_level l on l.tenant_id = i.tenant_id and l.skill_code = i.skill_set_code and l.difficulty = i.difficulty
  where i.status = 'active' and l.confirmed_at is not null
    and exists (select 1 from question_type_approval a
                where a.tenant_id = i.tenant_id and a.question_type = q.question_type)
    and not exists (select 1 from kind_stopped k
                    where k.tenant_id = i.tenant_id and k.skill_code = i.skill_set_code and k.difficulty = i.difficulty
                      and k.question_type = q.question_type);

-- The engine writes; the website reads.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on skill_level_kind_stop to app_engine;
    grant select on kind_stopped to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on skill_level_kind_stop, kind_stopped to app_web;
  end if;
end $$;

select internal.apply_conventions();
