-- A waiting note cleared by a person, and what she can approve so the next note needs no one (goals/m1-16-materials-
-- consolidated.yaml, brick 2; task M1-16; D-074). ADDITIVE ONLY, written to run twice. Needs 20270104090000.
--
--   * materials_note_review          gains the two ways a waiting note ends: 'added' (a person put it on the list through the
--                                    same path as any line) or 'dismissed' (with her reason). Who, when, and what she added
--                                    are kept on the row; the note's words are never changed. A waiting note has no ending.
--   * material_alias                 a word the school uses for a catalogue item ("ball pen"), approved by a person. It is
--                                    handed to the model beside the item; code still decides what is confirmed.
--   * material_unit_conversion       a unit that converts to an item's own ("dozen" -> 12 piece), approved by a person. Code
--                                    converts only with one of these rows; without one a different unit waits for a person.
--                                    Append-only: a changed factor is a new row and the latest is used.
--
-- No child's name and no rupee value is held here.

alter table materials_note_review add column if not exists resolved_by       uuid references staff(id);
alter table materials_note_review add column if not exists resolved_at       timestamptz;
alter table materials_note_review add column if not exists resolved_code     text;
alter table materials_note_review add column if not exists resolved_quantity numeric;
alter table materials_note_review add column if not exists why               text;
alter table materials_note_review add column if not exists updated_at        timestamptz not null default now();  -- a note is now changed once, so the table's touch trigger needs it

alter table materials_note_review drop constraint if exists materials_note_review_state_check;
alter table materials_note_review
  add constraint materials_note_review_state_check check (state in ('needs_person', 'added', 'dismissed'));
alter table materials_note_review drop constraint if exists materials_note_review_ending_check;
alter table materials_note_review
  add constraint materials_note_review_ending_check check (
    (state = 'needs_person' and resolved_by is null and resolved_at is null)
    or (state = 'added' and resolved_by is not null and resolved_at is not null
        and resolved_code is not null and resolved_quantity > 0)
    or (state = 'dismissed' and resolved_by is not null and resolved_at is not null and btrim(coalesce(why, '')) <> '')
  );
create index if not exists materials_note_review_open_idx on materials_note_review (tenant_id, at) where state = 'needs_person';

create table if not exists material_alias (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  alias         text not null check (alias = lower(btrim(alias)) and alias <> ''),
  material_code text not null,
  approved_by   uuid not null references staff(id),
  approved_at   timestamptz not null default clock_timestamp(),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code),
  unique (tenant_id, alias)
);

create index if not exists material_alias_item_idx on material_alias (tenant_id, material_code);

create table if not exists material_unit_conversion (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  material_code text not null,
  from_unit     text not null check (from_unit = lower(btrim(from_unit)) and from_unit <> ''),
  factor        numeric not null check (factor > 0 and factor < 'Infinity'),
  approved_by   uuid not null references staff(id),
  approved_at   timestamptz not null default clock_timestamp(),
  foreign key (tenant_id, material_code) references material_item (tenant_id, code)
);
-- Append-only: a changed factor is a new row, the latest is the one used, and the old one stays to show who approved what when.
create index if not exists material_unit_conversion_latest_idx
  on material_unit_conversion (tenant_id, material_code, from_unit, approved_at desc);
drop trigger if exists material_unit_conversion_append_only on material_unit_conversion;
create trigger material_unit_conversion_append_only before update or delete on material_unit_conversion
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
