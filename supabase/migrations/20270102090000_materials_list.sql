-- The K2 educator's materials list (goals/m1-10-materials-list.yaml; task M1-10; decisions D-070, D-071, D-072).
-- Built by code from the planned activities' materials, grouped by day, week or fortnight, edited by the educator, sent
-- to the materials team, with reminders. No model writes any of it.
--
--   * materials_list        one list for one class over a range of dates, drafted or sent.
--   * materials_line        one catalogue item on a list (its unit is the item's, copied when the line is made): its quantity (null when the sheet gives none,
--                           never invented), the first day it is needed and the activity it is first needed for.
--                           `source` says whether the school's plan made the line or the educator added it. A line the
--                           educator removes is marked, not deleted, so a rebuild does not bring it back.
--   * materials_line_source every session (its activity and day) that adds to a line, so the line stays tied to its
--                           activities and its sources add up to its quantity.
--   * materials_line_edit   every change by the educator (added, quantity changed, removed) with who and when and the
--                           line before and after. Append-only.
--   * material_item_proposal  a catalogue item an educator added, who added it, and that it waits for a person.
--   * materials_send        exactly what was sent, by which route, who tapped and when. Append-only: what was sent is
--                           never rewritten. Whether it was read cannot be known (D-071).
--   * materials_send_ack    the educator's "the team has it" tick on a send. A new row, never an edit.
--   * reminder              when to remind the educator and the materials team: the lead times are a setting, the date
--                           is computed by code. Cancelled, never repeated, once the list is sent.
--
-- Not here: the home of an item (class or school) and its rupee value (M1-13, on `material_item`); a catalogue item an
-- educator adds is a `material_item` with no home and no value, which already means "needs a person". No child's name
-- is held. ADDITIVE ONLY, and written to run twice. Needs 20270101090000 (M1-11: material_item, activity_material).

create table if not exists materials_list (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  school_class_id uuid not null references school_class(id),
  period          text not null check (period in ('day', 'week', 'fortnight')),
  from_on         date not null,
  to_on           date not null,
  state           text not null default 'draft' check (state in ('draft', 'sent')),
  built_at        timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (to_on >= from_on),
  unique (school_class_id, period, from_on, to_on)
);

create table if not exists materials_line (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  list_id       uuid not null references materials_list(id) on delete cascade,
  material_code text not null,
  unit          text not null check (btrim(unit) <> ''),
  quantity      numeric check (quantity > 0),
  needed_on     date not null,
  activity_code text,
  source        text not null default 'school' check (source in ('school', 'educator')),
  removed_at    timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code),
  foreign key (tenant_id, activity_code) references activity (tenant_id, code),
  check (source = 'educator' or activity_code is not null),
  unique (list_id, material_code)
);

create table if not exists materials_line_source (
  line_id       uuid not null references materials_line(id) on delete cascade,
  session_id    uuid not null references session(id) on delete cascade,
  activity_code text not null,
  on_date       date not null,
  quantity      numeric check (quantity > 0),
  primary key (line_id, session_id)
);

create table if not exists materials_line_edit (
  id         uuid primary key default gen_random_uuid(),
  tenant_id  uuid not null references tenant(id) on delete cascade,
  list_id    uuid not null references materials_list(id),
  line_id    uuid not null references materials_line(id),
  kind       text not null check (kind in ('add', 'quantity', 'remove')),
  who        uuid not null references staff(id),
  at         timestamptz not null default clock_timestamp(),
  before     jsonb,
  after      jsonb
);
create index if not exists materials_line_edit_list_idx on materials_line_edit (list_id);
drop trigger if exists materials_line_edit_append_only on materials_line_edit;
create trigger materials_line_edit_append_only before update or delete on materials_line_edit
  for each statement execute function internal.forbid_change();

create table if not exists material_item_proposal (
  tenant_id     uuid not null references tenant(id) on delete cascade,
  material_code text not null,
  state         text not null default 'needs_person' check (state in ('needs_person')),
  who           uuid not null references staff(id),
  at            timestamptz not null default clock_timestamp(),
  primary key (tenant_id, material_code),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code)
);

create table if not exists materials_send (
  id        uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenant(id) on delete cascade,
  list_id   uuid not null references materials_list(id),
  route     text not null check (route in ('whatsapp', 'email')),
  text      text not null check (btrim(text) <> ''),
  status    text not null check (status in ('opened', 'sent', 'not configured', 'failed')),  -- whatsapp: 'opened'; email: 'not configured', 'sent', 'failed'
  who       uuid not null references staff(id),
  at        timestamptz not null default clock_timestamp()
);
create index if not exists materials_send_list_idx on materials_send (list_id);
drop trigger if exists materials_send_append_only on materials_send;
create trigger materials_send_append_only before update or delete on materials_send
  for each statement execute function internal.forbid_change();

create table if not exists materials_send_ack (
  send_id uuid primary key references materials_send(id),
  who     uuid not null references staff(id),
  at      timestamptz not null default clock_timestamp()
);

create table if not exists reminder (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  list_id      uuid not null references materials_list(id) on delete cascade,
  weeks_before int not null check (weeks_before > 0),
  audience     text not null check (audience in ('educator', 'team')),
  due_on       date not null,
  at_once      boolean not null default false,
  state        text not null default 'pending' check (state in ('pending', 'cancelled')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (list_id, weeks_before, audience)
);
create index if not exists reminder_due_idx on reminder (due_on) where state = 'pending';

select internal.apply_conventions();
