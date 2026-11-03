-- The K2 team's activity sheet becomes the K2 curriculum (goals/m0-02-k2-curriculum-upload.yaml, task M0-02).
-- Nimish, D-050: "We just need activities to learning objectives. We'll consider that as an upload. People can
-- actually go and edit if they have to." There is no signing step; what a person needs is the history of who changed
-- what, and when.
--
-- Additive only: three columns on `activity`, one link table, one history ledger. No row is changed, dropped or
-- deleted, and no existing column is touched. Written to run twice.
--   activity.materials   the sheet's TLMs: what the educator lays out for the activity
--   activity.level_0     the sheet's "Activity Level 0" (the child who does not sit for the class)
--   activity.sheet_no    the K2 team's own activity number, as typed ('' where the sheet shows none or #REF!)
--   activity_objective   which learning objectives an activity names, in the order the sheet lists them. The
--                        objectives themselves are `learning_objective` rows of band K2, so nothing new is invented
--                        for them (their `signal` is '' until the team classifies one: a column the table already has)
--   curriculum_edit      one row per field a person or an upload changed on an activity or a learning objective:
--                        what it was, what it became, who, when. Written by a trigger, so every route (the site, the
--                        engine, a script) is kept; never changed after (rule 4).

alter table activity
  add column if not exists materials text not null default '',
  add column if not exists level_0   text not null default '',
  add column if not exists sheet_no  text not null default '';

create table if not exists activity_objective (
  tenant_id      uuid not null references tenant(id) on delete cascade,
  activity_code  text not null,
  lo_code        text not null,
  ord            integer not null check (ord >= 1),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  primary key (tenant_id, activity_code, lo_code),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code) on delete cascade,
  foreign key (tenant_id, lo_code) references learning_objective (tenant_id, code) on delete cascade
);
create index if not exists activity_objective_by_lo_idx on activity_objective (tenant_id, lo_code);

create table if not exists curriculum_edit (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  record      text not null check (record in ('activity', 'learning_objective')),
  code        text not null,                 -- the activity's or objective's code, e.g. ACT-K2-0085
  field       text not null,
  before      text not null,
  after       text not null,
  changed_by  text not null check (btrim(changed_by) <> ''),
  created_at  timestamptz not null default clock_timestamp(),
  updated_at  timestamptz not null default now()
);
create index if not exists curriculum_edit_by_code_idx on curriculum_edit (tenant_id, record, code, created_at);

drop trigger if exists curriculum_edit_kept on curriculum_edit;
create trigger curriculum_edit_kept before update or delete on curriculum_edit
  for each statement execute function internal.forbid_change();

-- Who: the caller says it for the transaction (`set_config('app.changed_by', 'Name or upload label', true)`); a write
-- that does not say is kept under the database role that made it, never dropped.
create or replace function internal.curriculum_edit_kept() returns trigger
language plpgsql set search_path = public as $$
declare
  who text := coalesce(nullif(btrim(current_setting('app.changed_by', true)), ''), session_user::text);
  f text;
  was text;
  now_ text;
begin
  foreach f in array tg_argv loop
    execute format('select ($1).%I::text', f) into was using old;
    execute format('select ($1).%I::text', f) into now_ using new;
    if was is distinct from now_ then
      insert into curriculum_edit (tenant_id, record, code, field, before, after, changed_by)
      values (new.tenant_id, tg_table_name, new.code, f, coalesce(was, ''), coalesce(now_, ''), who);
    end if;
  end loop;
  return new;
end $$;

drop trigger if exists activity_edit_kept on activity;
create trigger activity_edit_kept after update on activity
  for each row execute function internal.curriculum_edit_kept(
    'strand', 'name', 'objective', 'materials', 'level_0', 'level_1', 'level_2', 'level_3', 'sheet_no');

drop trigger if exists learning_objective_edit_kept on learning_objective;
create trigger learning_objective_edit_kept after update on learning_objective
  for each row execute function internal.curriculum_edit_kept('subject', 'unit', 'title');

-- The engine writes (the upload); the website reads, and a person's edit of an activity goes through it later (S6).
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert, update, delete on activity_objective to app_engine;
    grant select, insert on curriculum_edit to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on activity_objective, curriculum_edit to app_web;
  end if;
end $$;

select internal.apply_conventions();
