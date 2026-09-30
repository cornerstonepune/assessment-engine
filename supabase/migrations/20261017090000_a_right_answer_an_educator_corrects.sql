-- A paper question's right answer, changed by an educator for every child (goals/s26-the-right-answer-shown-and-
-- corrected.yaml, ADR 0045). Append-only: the latest row for a question is its key. Every deploy enters each paper
-- again from its file, and `engine legacy paper` puts the latest row back over the file's key after it, so a
-- correction made on the Marking page is never undone by the next deploy.
create table key_correction (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  item_key    text not null,                 -- legacy/<paper>/<question>, as the paper's item names it
  was         text,                          -- the right answer it replaced, as stored then
  answer      text not null,                 -- the right answer from now on
  by          text not null,
  created_at  timestamptz not null default clock_timestamp(),
  updated_at  timestamptz not null default now()
);
create index key_correction_item_idx on key_correction (tenant_id, item_key, created_at desc);

create trigger key_correction_append_only before update or delete on key_correction
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
