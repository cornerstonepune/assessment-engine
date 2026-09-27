-- A wrong answer no named mistake explains is named by a person, picking from Jev's shortlist (ADR 0036,
-- goals/j2-name-the-mistake.yaml). Append-only (rule 4's spirit for anything a person says): naming again is a new
-- row, and the latest row for an answer stands — but only for the reading it was named on (`answer`), so a
-- different reading of the child's writing is named afresh.
create table mistake_named (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  item_result_id uuid not null references item_result(id),
  answer         text not null,               -- what the child wrote, as the person had it when they named it
  code           text not null,               -- a named mistake's code, or NONE: none of them
  proposed       jsonb not null default '[]', -- Jev's shortlist as the person saw it: [[code, chance], …]
  by             text not null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index mistake_named_item_result_idx on mistake_named (item_result_id);

create trigger mistake_named_append_only
  before update or delete on mistake_named
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
