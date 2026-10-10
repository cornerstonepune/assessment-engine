-- A story is its numbers, its shape and its operations (goals/as2-a-story-is-its-shape.yaml, ADR 0053), so a story
-- stored before its shape was in its key is keyed again by `engine bank rekey`. Append-only: each row says one
-- question's key changed, from what to what. A row that named the question by its old key and is never rewritten — a
-- proposal in its own append-only ledger, a gold file written before, a page bookmarked — finds it through here.
create table item_key_change (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  item_id     uuid not null references item(id) on delete cascade,
  old_key     text not null,
  new_key     text not null,
  why         text not null,
  created_at  timestamptz not null default clock_timestamp(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, old_key)
);
create index item_key_change_item_idx on item_key_change (item_id);

create trigger item_key_change_append_only before update or delete on item_key_change
  for each statement execute function internal.forbid_change();

-- The key a question has now, from any key it has had: the one rule every reader of an old key uses (the engine's
-- `inventory.current_key`, a gold file loaded, the website's question page). A key with no change is itself.
create or replace function public.current_item_key(p_key text)
returns text
language sql stable as $$
  with recursive k(key, n) as (
    select p_key, 0
    union all
    select c.new_key, k.n + 1 from item_key_change c join k on c.old_key = k.key where k.n < 8
  )
  select key from k order by n desc limit 1
$$;
grant execute on function public.current_item_key(text) to app_web, app_engine;

select internal.apply_conventions();
