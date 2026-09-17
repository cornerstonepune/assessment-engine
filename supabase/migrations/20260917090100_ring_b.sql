-- Ring B — derived. TRUNCATE-able at any time; a pure function of Ring A,
-- rebuilt nightly by `engine graph` from confirmed evidence only.
-- All three are created empty; Phase 1's graph rebuild is the first writer.

create table child_skill_state (
  id                       uuid primary key default gen_random_uuid(),
  tenant_id                uuid not null references tenant(id) on delete cascade,
  child_id                 uuid not null references child(id) on delete cascade,
  skill_code               text not null,
  rung_code                text not null,
  state                    text not null
                           check (state in ('not_enough_yet', 'patterned_error', 'emerging',
                                            'practising', 'secure', 'stretch_ready')),
  n_events                 integer not null default 0,
  n_correct                integer not null default 0,
  repeating_misconception  text,
  last_seen                timestamptz,
  computed_at              timestamptz not null default now(),
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (tenant_id, child_id, skill_code, rung_code)
);
create index child_skill_state_child_idx on child_skill_state (child_id);

create table class_card (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  section      text not null,
  week         text not null,
  rung_code    text not null,
  secure       uuid[] not null default '{}',          -- child ids
  reteach      jsonb not null default '{}'::jsonb,    -- {misconception_code: [child_id, ...]}
  move_up      uuid[] not null default '{}',
  computed_at  timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, section, week, rung_code)
);

create table item_stat (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenant(id) on delete cascade,
  item_id              uuid not null references item(id) on delete cascade,
  n                    integer not null default 0,
  p_correct            numeric(5, 4),
  flagged_mislevelled  boolean not null default false,
  computed_at          timestamptz not null default now(),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (tenant_id, item_id)
);
create index item_stat_item_idx on item_stat (item_id);

select internal.apply_conventions();
