-- An error a page of the website raised, recorded by the page's pattern so the live watcher can say so within ten
-- minutes (goals/p2-live-is-watched.yaml). No message: it can carry a child's name, and Vercel's own log keeps it,
-- found by the digest.
create table web_error (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  route       text not null,   -- the page's pattern as Next names it (/growth/[id]), never an address with its ids
  kind        text not null,   -- render, route, action or proxy
  digest      text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index web_error_recent_idx on web_error (created_at desc);

grant insert on web_error to app_web;

select internal.apply_conventions();
