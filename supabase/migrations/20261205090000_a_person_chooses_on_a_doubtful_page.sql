-- When the engine finds that a page in a scan may not belong to the child its answers are filed under (the same picture
-- on two children's copies, or a printed code that is another child's), a person says which it is before the answer can be
-- confirmed. One row per choice, never updated: a changed mind is a new row, and the latest stands (rule 4).
-- Additive: nothing existing is read or changed.
create table if not exists page_choice (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  capture_id  uuid not null references capture(id) on delete cascade,
  file_page   integer not null check (file_page > 0),
  problem     text not null check (problem in ('same_picture', 'wrong_code')),
  choice      text not null check (choice in ('theirs', 'not_theirs')),
  by          text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists page_choice_capture_idx on page_choice (capture_id, file_page, created_at desc);

create trigger page_choice_append_only before update or delete on page_choice
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
