-- A member of staff sets their own password from a one-time link sent to their email: "Forgot your password?" on the
-- sign-in page, or the first link a new person gets when they are added on the Staff page (goals/auth-email-password.yaml).
-- Only the sha-256 of a link's token is kept, never the token: a row read by anyone opens nothing. A link works while
-- it is neither used nor closed and its time is not up; asking again, using one, or changing the password closes the
-- rest. The limits are threshold rows, `password_link.*` and `password_ask.*`. Additive: nothing existing changes.
create table password_link (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  email       text not null,                       -- lowercased, as on the staff list
  token_hash  text not null unique,                -- hex sha-256 of the 32 random bytes sent in the link
  purpose     text not null check (purpose in ('reset', 'first')),
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null,
  used_at     timestamptz,
  closed_at   timestamptz,
  mail        text check (mail in ('sent', 'not configured', 'failed')),  -- what became of the email, never why
  updated_at  timestamptz not null default now()
);
create index password_link_open_idx on password_link (email) where closed_at is null;

-- Each "Forgot your password?" asked, known email or not, so the form is limited per email and per address as the
-- sign-in page is (sign_in_failure). `ip` is an HMAC of the address under the site's secret, never the address.
create table password_ask (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  email       text not null,
  ip          text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index password_ask_email_idx on password_ask (email, created_at desc);
create index password_ask_ip_idx on password_ask (ip, created_at desc);

-- The website makes and spends links, and records each ask; it changes no other column.
grant insert on password_link, password_ask to app_web;
grant update (used_at, closed_at, mail) on password_link to app_web;

select internal.apply_conventions();
