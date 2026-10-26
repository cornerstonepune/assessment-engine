-- A scan file's page is told once: its picture's fingerprint and the code printed on it, facts of a file that never
-- changes. Check answers drew the photograph of every page of every copy in a scan file on each card to tell whose
-- paper it is, about half a second a page and some 8 seconds a click (docs/notes/perf-slow-site.md); it reads these rows.
-- One row per page, written once and never changed (rule 4). Additive: nothing existing is read or changed.
create table if not exists capture_page (
  capture_id  uuid not null references capture(id) on delete cascade,
  file_page   integer not null check (file_page > 0),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  print       text not null,
  code        text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  primary key (capture_id, file_page)
);

create trigger capture_page_append_only before update or delete on capture_page
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
