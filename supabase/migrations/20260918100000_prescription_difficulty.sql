-- W2: a prescription names a skill set and a difficulty, not a level.
--
-- Ring A was written before the school's own vocabulary was settled. `level` (Lm/L0/Lp) was a
-- parallel invention and is retired (DECISIONS-LOG, 2026-09-17); the school says Easy / Medium /
-- Hard / Advance, and a prescription reads "Kabir: SUB.2D.EXCH at Hard". The old columns stay,
-- nullable, so nothing that was written against them breaks.

alter table prescription
  add column skill_set_code text,
  add column difficulty     text check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance')),
  add column kind           text not null default 'practice'
                            check (kind in ('practice', 'assessment', 'home')),
  alter column level drop not null,
  alter column strand drop not null;
alter table prescription drop constraint prescription_level_check;
alter table prescription
  add constraint prescription_level_check check (level is null or level in ('Lm', 'L0', 'Lp'));

-- One prescription per child per week per kind. Re-running the prescriber must not double up.
create unique index prescription_one_per_child_week_kind
  on prescription (tenant_id, child_id, week, kind);

alter table sheet_template
  add column skill_set_code text,
  add column difficulty     text check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance')),
  add column child_id       uuid references child(id),   -- null for a spare
  alter column level drop not null;
alter table sheet_template drop constraint sheet_template_level_check;
alter table sheet_template
  add constraint sheet_template_level_check check (level is null or level in ('Lm', 'L0', 'Lp'));
create index sheet_template_child_idx on sheet_template (child_id);

-- Which child has already seen which item, so the picker never repeats one inside the window.
-- Written when a sheet is assembled, not when it is marked: a child has seen a printed question
-- whether or not they answered it.
create table item_exposure (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  child_id    uuid not null references child(id) on delete cascade,
  item_id     uuid not null references item(id) on delete cascade,
  week        text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, child_id, item_id)
);
create index item_exposure_child_idx on item_exposure (child_id, created_at desc);
create index item_exposure_item_idx on item_exposure (item_id);

select internal.apply_conventions();
