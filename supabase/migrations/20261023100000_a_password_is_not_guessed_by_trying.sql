-- A wrong password for an email, kept so the sign-in page refuses that email for a while once there are too many
-- (goals/p2-live-recovers.yaml). The limits are threshold rows, `sign_in.*`.
create table sign_in_failure (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  email       text not null,   -- lowercased, as typed
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index sign_in_failure_recent_idx on sign_in_failure (email, created_at desc);

grant insert on sign_in_failure to app_web;

select internal.apply_conventions();
