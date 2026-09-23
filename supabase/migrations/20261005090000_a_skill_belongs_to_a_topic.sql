-- The shared tree (BUILD-ORDER, Nimish 2026-09-23): every screen reads grade → subject → topic → skill → level.
-- A topic is a row, as a subject is: "Addition & subtraction", "Estimation". Which skills a topic holds is data
-- (supabase/seed/topics.json), so regrouping them is an edit to a file, never to code.
create table topic (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  code         text not null,
  subject_code text not null,
  name         text not null,
  ord          int not null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, code)
);

alter table skill_set add column topic_code text;

select internal.apply_conventions();
