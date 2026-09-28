-- N4, the week's declaration (goals/n4-week-declaration.yaml): what an educator confirms their section did in a
-- week — their note in their own words, the skill sets they confirmed, and what the engine had proposed. Append-only:
-- declaring again is a new row, and the latest for a section and week stands.
create table week_declaration (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  section     text not null,
  week        text not null,                 -- as the week's papers name it
  note        text not null default '',
  skill_sets  text[] not null,
  proposed    jsonb not null default '[]',   -- the engine's proposal as the educator saw it: [{code, yes, ticked}]
  by          text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index week_declaration_week_idx on week_declaration (tenant_id, section, week, created_at desc);

create trigger week_declaration_append_only before update or delete on week_declaration
  for each statement execute function internal.forbid_change();

select internal.apply_conventions();
