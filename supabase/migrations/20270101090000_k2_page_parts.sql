-- M1-11: a K2 activity page with every part, and where each part came from (goals/m1-11-k2-complete-v1.yaml).
-- Nimish, 4 Nov: K2 version 1 has no empty part; the school's text is kept and marked the school's; what an agent drafts is
-- marked drafted until a person keeps, changes or rejects it (D-071).
--
-- Additive only, written to run twice. No row is changed, dropped or deleted.
--   activity.steps        what to do: the sheet's LESSON PLANS column, never stored before
--   activity.thinking     how it needs to be thought about: the educator's view of the idea and the common slips
--   activity_part_source  where one part of one page came from: school | drafted | person. A part with no row here has
--                         no source yet (an empty part, or one loaded before this table); the upload writes 'school'
--   material_item         the catalogue: one row per kind of thing, with its unit, its home (class or school) and its
--                         value per unit; the last two stay empty, and are flagged, until a person fills them
--   activity_material     which items an activity needs, how many, in the order the sheet lists them
--   curriculum_proposal   takes two more kinds, 'page_part' and 'material', so the M1-05 ledger carries these drafts

alter table activity
  add column if not exists steps    text not null default '',
  add column if not exists thinking text not null default '';

-- every field a person or an upload changes is kept with who and when (the trigger of M0-02, with the two new fields)
drop trigger if exists activity_edit_kept on activity;
create trigger activity_edit_kept after update on activity
  for each row execute function internal.curriculum_edit_kept(
    'strand', 'name', 'objective', 'materials', 'level_0', 'level_1', 'level_2', 'level_3', 'sheet_no',
    'steps', 'thinking');

create table if not exists activity_part_source (
  tenant_id      uuid not null references tenant(id) on delete cascade,
  activity_code  text not null,
  part           text not null check (part in
                   ('objective', 'steps', 'thinking', 'materials', 'level_0', 'level_1', 'level_2', 'level_3')),
  source         text not null check (source in ('school', 'drafted', 'person')),
  proposal_id    uuid references curriculum_proposal(id),  -- the draft this part came from, when it is drafted
  staff_id       uuid references staff(id),                -- the member of staff who kept or changed it (D-046: ids)
  check_me       boolean not null default false,           -- a draft the checker, the drafter or the confidence doubted: heads the review list
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  primary key (tenant_id, activity_code, part),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code) on delete cascade
);

create table if not exists material_item (
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,                     -- MAT-0001
  name        text not null check (btrim(name) <> ''),
  unit        text not null default 'piece' check (btrim(unit) <> ''),
  home        text check (home in ('class', 'school')),  -- where it is kept (D-072); empty until a person says
  unit_value  numeric check (unit_value >= 0),           -- rupees for one unit; empty until a person says, never guessed
  proposal_id uuid references curriculum_proposal(id),   -- the machine proposal that made it; empty for a person's item
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (tenant_id, code),
  unique (tenant_id, name)
);

create table if not exists activity_material (
  tenant_id      uuid not null references tenant(id) on delete cascade,
  activity_code  text not null,
  material_code  text not null,
  quantity       numeric check (quantity > 0),  -- empty when the school's text gives none: never guessed
  ord            integer not null check (ord >= 1),
  source         text not null default 'person' check (source in ('person', 'machine')),
  proposal_id    uuid references curriculum_proposal(id),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  primary key (tenant_id, activity_code, material_code),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code) on delete cascade,
  foreign key (tenant_id, material_code) references material_item (tenant_id, code)
);
create index if not exists activity_material_by_item_idx on activity_material (tenant_id, material_code);

alter table curriculum_proposal drop constraint if exists curriculum_proposal_kind_check;
alter table curriculum_proposal add constraint curriculum_proposal_kind_check
  check (kind in ('skill', 'objective', 'levels', 'lo_skill', 'page_part', 'material'));

do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert, update, delete on activity_part_source, material_item, activity_material to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on activity_part_source, material_item, activity_material to app_web;
  end if;
end $$;

select internal.apply_conventions();
