-- The school's consolidated materials list (goals/m1-16-materials-consolidated.yaml; task M1-16; decisions D-071, D-072,
-- D-074). Built by code from every class's list (M1-10), summed per catalogue item, each line keeping which classes and
-- activities it comes from; every build is kept, so a later build shows what changed; sent to the one inventory person.
--
--   * materials_consolidated         one list for the school over a range of dates (a month), and how many builds it has had.
--   * materials_consolidated_line    a build's line: one catalogue item, its total (null when a class gave none: the total is
--                                    then unknown, never a smaller number) and whether it needs confirming.
--   * materials_consolidated_source  which class asked for how much of a line, and for which activities.
--   * materials_consolidated_change  what moved between a build and the one before it (added, removed, quantity). Append-only.
--   * materials_consolidated_send    exactly what was sent to the inventory person, who tapped and when, with the lines as
--                                    sent so the next send can say what changed. Append-only. Delivery cannot be known.
--   * materials_note_review          a request a model read but code could not confirm: it waits for a person and is not
--                                    in any list. A photograph is never stored, so no image is referenced here.
--
-- Rupee values are not here (M1-13). No child's name is held. ADDITIVE ONLY, written to run twice.
-- Needs 20270102090000 (M1-10) and 20270101090000 (M1-11: material_item).

create table if not exists materials_consolidated (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  from_on      date not null,
  to_on        date not null,
  latest_build int not null default 0 check (latest_build >= 0),
  skipped_lists uuid[] not null default '{}',  -- lists left out of the latest build because they overlapped a wider one of the same class
  built_at     timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  check (to_on >= from_on),
  unique (tenant_id, from_on, to_on)
);

create table if not exists materials_consolidated_line (
  tenant_id       uuid not null references tenant(id) on delete cascade,
  consolidated_id uuid not null references materials_consolidated(id) on delete cascade,
  build           int not null check (build > 0),
  material_code   text not null,
  unit            text not null check (btrim(unit) <> ''),
  quantity        numeric check (quantity > 0),
  to_confirm      boolean not null,
  primary key (consolidated_id, build, material_code),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code),
  check (to_confirm = (quantity is null))
);

create table if not exists materials_consolidated_source (
  consolidated_id uuid not null,
  build           int not null,
  material_code   text not null,
  class_id        uuid not null references school_class(id),
  quantity        numeric check (quantity > 0),
  activity_codes  text[] not null default '{}',
  primary key (consolidated_id, build, material_code, class_id),
  foreign key (consolidated_id, build, material_code)
    references materials_consolidated_line (consolidated_id, build, material_code) on delete cascade
);

create table if not exists materials_consolidated_change (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  consolidated_id uuid not null references materials_consolidated(id),
  build           int not null check (build > 1),
  material_code   text not null,
  kind            text not null check (kind in ('added', 'removed', 'quantity')),
  before          numeric,
  after           numeric,
  class_ids       uuid[] not null default '{}',
  at              timestamptz not null default clock_timestamp(),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code)
);
create index if not exists materials_consolidated_change_idx on materials_consolidated_change (consolidated_id, build);
drop trigger if exists materials_consolidated_change_append_only on materials_consolidated_change;
create trigger materials_consolidated_change_append_only before update or delete on materials_consolidated_change
  for each statement execute function internal.forbid_change();

create table if not exists materials_consolidated_send (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  consolidated_id uuid not null references materials_consolidated(id),
  build           int not null check (build > 0),
  text            text not null check (btrim(text) <> ''),
  lines           jsonb not null,
  status          text not null check (status in ('opened', 'sent', 'not configured', 'failed')),
  who             uuid not null references staff(id),
  at              timestamptz not null default clock_timestamp()
);
create index if not exists materials_consolidated_send_idx on materials_consolidated_send (consolidated_id, at);
drop trigger if exists materials_consolidated_send_append_only on materials_consolidated_send;
create trigger materials_consolidated_send_append_only before update or delete on materials_consolidated_send
  for each statement execute function internal.forbid_change();

create table if not exists materials_note_review (
  id        uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  list_id   uuid not null references materials_list(id),
  text      text not null,
  reason    text not null check (btrim(reason) <> ''),
  state     text not null default 'needs_person' check (state in ('needs_person')),
  who       uuid not null references staff(id),
  at        timestamptz not null default clock_timestamp()
);
create index if not exists materials_note_review_list_idx on materials_note_review (list_id);

select internal.apply_conventions();
