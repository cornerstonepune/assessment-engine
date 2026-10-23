-- A consent and data register (goals/c6-consent-and-data-register.yaml, the locked scope of 22 Oct, slice C6): what is
-- kept about a child, why, how long, who sees it, in a parent's words.
--
--   data_register  one entry for each kind of thing kept about a child, in a parent's words, and the tables that hold
--                  it; written from supabase/seed/data_register.json by `engine load` (a lawyer's draft to check)
--   consent        a parent's answer for one child: given or withdrawn, how, who at the school recorded it, and a
--                  fingerprint of the register's words as they stood, so what was agreed to can be shown later.
--                  Never edited: a change of mind is a new row. It holds the child's id only (rule 6: names stay in
--                  `pii`), and says the parent's relation to the child, never their name
--   consent_now    each child's latest answer
--
-- Written to run twice.

create table if not exists data_register (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  ord         int not null,
  what        text not null check (btrim(what) <> ''),
  why         text not null check (btrim(why) <> ''),
  how_long    text not null check (btrim(how_long) <> ''),
  who_sees    text not null check (btrim(who_sees) <> ''),
  tables      text[] not null check (cardinality(tables) > 0),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists consent (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  child_id     uuid not null references child(id) on delete cascade,
  decision     text not null check (decision in ('given', 'withdrawn')),
  given_by     text not null check (btrim(given_by) <> ''),   -- the parent's relation to the child, never a name
  how          text not null check (btrim(how) <> ''),        -- a signed form, in person, …
  recorded_by  text not null check (btrim(recorded_by) <> ''),
  register     text,                                          -- the register's words as they stood, fingerprinted
  created_at   timestamptz not null default clock_timestamp(), -- an answer changed in one sitting is still later
  updated_at   timestamptz not null default now()
);
create index if not exists consent_child_idx on consent (child_id, created_at);

drop trigger if exists consent_kept on consent;
create trigger consent_kept before update or delete on consent
  for each statement execute function internal.forbid_change();

-- The register a parent answered: every entry's words, in order, as one fingerprint.
create or replace function internal.data_register_fingerprint(p_tenant uuid) returns text
language sql stable security definer set search_path = public as $$
  select md5(coalesce(string_agg(concat_ws('|', code, what, why, how_long, who_sees), chr(10) order by ord, code), ''))
  from data_register where tenant_id = p_tenant
$$;

create or replace function internal.consent_names_its_register() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from data_register where tenant_id = new.tenant_id) then
    raise exception 'there is no data register to consent to yet' using errcode = 'check_violation';
  end if;
  new.register := internal.data_register_fingerprint(new.tenant_id);
  return new;
end $$;
drop trigger if exists consent_names_its_register on consent;
create trigger consent_names_its_register before insert on consent
  for each row execute function internal.consent_names_its_register();

create or replace view consent_now with (security_invoker = true) as
select distinct on (c.child_id) c.tenant_id, c.child_id, c.decision, c.given_by, c.how, c.recorded_by, c.created_at,
       c.register = internal.data_register_fingerprint(c.tenant_id) as register_unchanged
from consent c
order by c.child_id, c.created_at desc, c.id desc;

select internal.apply_conventions();
