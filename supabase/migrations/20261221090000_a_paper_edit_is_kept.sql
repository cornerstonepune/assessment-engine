-- An educator removes a question from a child's paper, or adds one from the bank, on the paper's review page
-- (goals/paper_review_add_remove.yaml). Nimish, 2026-10-27: "one can remove a specific question and then can add another
-- question from the bank".
--
-- A paper is never changed in place: its code, layout, boxes and key belong to whatever was printed with that code. An
-- edit makes the paper again with a new code (engine/w2_print/edit_paper.py), sets the old copy void, and writes one row
-- here, never changed (rule 4):
--   paper_edit  which paper became which, what was removed or added (question ids), where, who, when, and whether it
--               withdrew an approval. Codes and ids only, never a child's name (rule 6).
-- Additive: no existing table, column or row is changed. Written to run twice.

create table if not exists paper_edit (
  id                 uuid primary key default gen_random_uuid(),
  tenant_id          uuid not null references tenant(id) on delete cascade,
  child_id           uuid references child(id),
  qr_before          text not null,
  qr_after           text not null,
  removed            uuid[] not null default '{}',
  added              uuid[] not null default '{}',
  at_position        integer,                       -- where an added question was put, 1 the first
  withdrew_approval  boolean not null,              -- the paper was approved, and now waits again
  changed_by         text not null check (btrim(changed_by) <> ''),
  created_at         timestamptz not null default clock_timestamp(),
  updated_at         timestamptz not null default now()
);
create index if not exists paper_edit_before_idx on paper_edit (tenant_id, qr_before);
create index if not exists paper_edit_after_idx on paper_edit (tenant_id, qr_after);

drop trigger if exists paper_edit_kept on paper_edit;
create trigger paper_edit_kept before update or delete on paper_edit
  for each statement execute function internal.forbid_change();

-- The engine writes; the website reads.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on paper_edit to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on paper_edit to app_web;
  end if;
end $$;

select internal.apply_conventions();
