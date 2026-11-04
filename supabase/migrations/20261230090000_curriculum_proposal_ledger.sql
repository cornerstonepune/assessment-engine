-- The curriculum mapping agents' ledger (goals/m1-05-mapping-agents.yaml, task M1-05). Additive: one new table, two
-- nullable columns on each of the three link tables, a wider list of records the edit history keeps, and one trigger
-- per link table; nothing existing is dropped or rewritten.
--
-- Nimish, 2026-11-03: "one agent that develops for all the places where you don't have descriptions, the right
-- learning objectives, or the skill mapping … another validation agent is also needed, so we don't have to wait for
-- manual input from teachers." A model proposes, code checks, a second model reads it, a person sees what is in doubt
-- (engine/w1_bank/map_*.py). Every step of that is a row here:
--   * curriculum_proposal  one row per proposal for one gap of one activity or objective, as it was decided
--                          (auto_passed, needs_person, rejected), what made it (the prompt versions, or code), what the
--                          checks found, the validator's verdict and the confidence. Never edited or deleted: a
--                          person's yes or no, an apply and a revert are each a new row naming the proposal (`about`).
--                          Who is a staff id and a fixed machine code, never a typed name (D-046).
--   * activity_skill, activity_objective, learning_objective_skill gain `source` (person | machine) and
--                          `proposal_id`: a machine-made link names the proposal that made it, so every one can be
--                          listed and reverted, and whatever is built from the links is rebuilt from them.
--   * curriculum_edit      now keeps every link added or removed, by anyone (P-09: links could be changed untraced,
--                          against D-050), beside the field edits it already kept.
--
-- Written to run twice.

create table if not exists curriculum_proposal (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  about               uuid references curriculum_proposal(id),  -- the proposal this row moves on; null on a proposal
  run_id              uuid not null,                            -- one `engine curriculum propose`
  kind                text not null check (kind in ('skill', 'objective', 'levels', 'lo_skill')),
  subject_code        text not null check (btrim(subject_code) <> ''),  -- an activity's code, or an objective's
  proposal            jsonb not null default '{}'::jsonb,
  confidence          numeric check (confidence between 0 and 1),
  proposer            text not null default '',                 -- curriculum_map_propose v1, or code
  validator           text not null default '',                 -- curriculum_map_validate v1, or none
  problems            text[] not null default '{}',             -- what the code checks found
  verdict             text not null default '' check (verdict in ('', 'agree', 'disagree')),
  status              text not null check (status in ('auto_passed', 'needs_person', 'rejected', 'approved',
                                                      'applied', 'reverted')),
  reason              text not null default '',                 -- why it went where it went, in words
  curriculum_version  int,                                      -- the version in force when it was applied
  -- who, never by name (D-046, rule 6): the member of staff who ran the command or decided, and the machine's part
  staff_id            uuid references staff(id),
  machine             text check (btrim(machine) <> ''),  -- proposer:<prompt>, code:lo_skill, apply, revert
  created_at          timestamptz not null default clock_timestamp(),
  updated_at          timestamptz not null default now(),
  check (about is null or about <> id),
  check (staff_id is not null or machine is not null),
  check (status not in ('approved', 'rejected') or about is null or staff_id is not null),  -- a person's own answer
  -- a proposal is decided when it is made; what follows it is a person's yes or no, an apply or a revert
  check (case when about is null then status in ('auto_passed', 'needs_person', 'rejected')
              else status in ('approved', 'rejected', 'applied', 'reverted') end),
  foreign key (tenant_id, curriculum_version) references curriculum_version (tenant_id, number)
);
create index if not exists curriculum_proposal_about_idx on curriculum_proposal (about) where about is not null;
create index if not exists curriculum_proposal_subject_idx on curriculum_proposal (tenant_id, kind, subject_code);

drop trigger if exists curriculum_proposal_append_only on curriculum_proposal;
create trigger curriculum_proposal_append_only before update or delete on curriculum_proposal
  for each statement execute function internal.forbid_change();

alter table activity_skill
  add column if not exists source text not null default 'person' check (source in ('person', 'machine')),
  add column if not exists proposal_id uuid references curriculum_proposal(id);
alter table activity_objective
  add column if not exists source text not null default 'person' check (source in ('person', 'machine')),
  add column if not exists proposal_id uuid references curriculum_proposal(id);
alter table learning_objective_skill
  add column if not exists source text not null default 'person' check (source in ('person', 'machine')),
  add column if not exists proposal_id uuid references curriculum_proposal(id);

-- The edit history keeps the links too: one row for a link added (before empty) and one for a link removed (after
-- empty), the record being the link table and the code the activity's or objective's.
alter table curriculum_edit drop constraint if exists curriculum_edit_record_check;
alter table curriculum_edit add constraint curriculum_edit_record_check check (record in ('activity',
  'learning_objective', 'activity_skill', 'activity_objective', 'learning_objective_skill'));

create or replace function internal.curriculum_link_kept() returns trigger
language plpgsql set search_path = public as $$
declare
  who text := coalesce(nullif(btrim(current_setting('app.changed_by', true)), ''), session_user::text);
  row_ jsonb := to_jsonb(case when tg_op = 'DELETE' then old else new end);
  owner text := coalesce(row_->>'activity_code', row_->>'lo_code');
  field text := case when tg_table_name = 'activity_objective' then 'lo_code' else 'skill_code' end;
  linked text := row_->>field;
begin
  insert into curriculum_edit (tenant_id, record, code, field, before, after, changed_by)
  values ((row_->>'tenant_id')::uuid, tg_table_name, owner, field,
          case when tg_op = 'DELETE' then linked else '' end, case when tg_op = 'DELETE' then '' else linked end, who);
  return null;
end $$;

drop trigger if exists activity_skill_kept on activity_skill;
create trigger activity_skill_kept after insert or delete on activity_skill
  for each row execute function internal.curriculum_link_kept();
drop trigger if exists activity_objective_kept on activity_objective;
create trigger activity_objective_kept after insert or delete on activity_objective
  for each row execute function internal.curriculum_link_kept();
drop trigger if exists learning_objective_skill_kept on learning_objective_skill;
create trigger learning_objective_skill_kept after insert or delete on learning_objective_skill
  for each row execute function internal.curriculum_link_kept();

-- The engine writes the ledger and never deletes from it; the website reads it (the person's list, later).
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on curriculum_proposal to app_engine;
    revoke update, delete on curriculum_proposal from app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on curriculum_proposal to app_web;
    revoke insert, update, delete on curriculum_proposal from app_web;
  end if;
end $$;

select internal.apply_conventions();
