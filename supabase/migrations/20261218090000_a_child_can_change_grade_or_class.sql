-- A coordinator changes a child's grade, or moves them to another class (goals/mov_move_a_child.yaml).
-- Nimish, 27 Oct 2026: a child to be moved to Grade 4, and the data to be "in a structured way. It's not like some
-- hard-coded backend". Until now the only way to change `child.band` was to edit the roster file and load it, and a change
-- of class through the roster made a new `child` row (matched on class and roll), stranding the child's evidence.
--
--   * `child_move`: one row for every change, never changed or removed (rule 4): who, when, the child, the grade, class and
--     roll it was and became, and the reason the person typed. A child's id only, no name (rule 6). Rows are added only by
--     `move_child`; the website may read them (`internal.apply_conventions` takes update and delete from every ledger).
--   * `move_child(child, grade, class, roll, by, reason)`: the one place the rule lives, so the website and any command
--     say the same thing. In one transaction it checks (the grade is a row of `grade`; the class is a class that has
--     children; the roll is free in it), changes the child's own row, so the id and every answer, result and piece of
--     evidence stay with them, and appends the history row. It returns {"moved": true, ...} or {"moved": false,
--     "refused": why}, and a refusal changes nothing.
--   * What depends on the child's grade or class is brought up to date by the paths that already make it. `class_band`
--     is a function of the child rows, so both classes already say the new grade. The stored class card (ring B) of both
--     classes is dropped, to be rebuilt from the graph the next time it is asked for. A plan for a week still to come
--     with no paper made and no hand-set difficulty is withdrawn, so the paper maker plans it again at the new grade; a
--     paper already made, printed or not, is not touched.
--
-- Additive: nothing existing is read differently. Written to run twice.

create table if not exists child_move (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  child_id      uuid not null references child(id),
  from_band     text not null,
  from_section  text not null,
  from_roll_no  text not null,
  to_band       text not null,
  to_section    text not null,
  to_roll_no    text not null,
  reason        text not null default '' check (char_length(reason) <= 500),
  moved_by      text not null check (btrim(moved_by) <> ''),
  moved_at      timestamptz not null default now(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  foreign key (tenant_id, from_band) references grade (tenant_id, code),
  foreign key (tenant_id, to_band) references grade (tenant_id, code),
  check (from_band <> to_band or from_section <> to_section or from_roll_no <> to_roll_no)
);
create index if not exists child_move_child_idx on child_move (child_id, moved_at desc);
create index if not exists child_move_to_idx on child_move (tenant_id, to_section, to_roll_no);
create index if not exists child_move_from_idx on child_move (tenant_id, from_section, from_roll_no);

drop trigger if exists child_move_append_only on child_move;
create trigger child_move_append_only before update or delete on child_move
  for each statement execute function internal.forbid_change();

create or replace function public.move_child(
  p_child uuid, p_band text, p_section text, p_roll text, p_by text, p_reason text default ''
) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  c child%rowtype;
  p_section_t text := btrim(coalesce(p_section, ''));
  p_roll_t    text := btrim(coalesce(p_roll, ''));
  withdrawn   integer;
  made        integer;
  this_week   text := to_char(current_date, 'IYYY-"W"IW');
begin
  select * into c from child where id = p_child for update;
  if not found then return jsonb_build_object('moved', false, 'refused', 'no_such_child'); end if;
  if btrim(coalesce(p_by, '')) = '' then return jsonb_build_object('moved', false, 'refused', 'no_one'); end if;
  if p_roll_t !~ '^[A-Za-z0-9-]{1,8}$' then return jsonb_build_object('moved', false, 'refused', 'bad_roll'); end if;
  if not exists (select 1 from grade where tenant_id = c.tenant_id and code = p_band) then
    return jsonb_build_object('moved', false, 'refused', 'no_such_grade');
  end if;
  -- a class is one that has a child in it: a typed name that matches none is a typing slip, not a new class
  if p_section_t <> c.section and not exists (
    select 1 from child where tenant_id = c.tenant_id and section = p_section_t and active
  ) then
    return jsonb_build_object('moved', false, 'refused', 'no_such_class');
  end if;
  if p_band = c.band and p_section_t = c.section and p_roll_t = c.roll_no then
    return jsonb_build_object('moved', false, 'refused', 'nothing_changes');
  end if;
  if exists (
    select 1 from child where tenant_id = c.tenant_id and section = p_section_t and roll_no = p_roll_t and id <> c.id
  ) then
    return jsonb_build_object('moved', false, 'refused', 'roll_taken');
  end if;

  begin
    update child set band = p_band, section = p_section_t, roll_no = p_roll_t where id = c.id;
  exception when unique_violation then  -- someone took the roll between the check and the change
    return jsonb_build_object('moved', false, 'refused', 'roll_taken');
  end;
  insert into child_move (tenant_id, child_id, from_band, from_section, from_roll_no, to_band, to_section, to_roll_no,
                          reason, moved_by)
  values (c.tenant_id, c.id, c.band, c.section, c.roll_no, p_band, p_section_t, p_roll_t,
          btrim(coalesce(p_reason, '')), btrim(p_by));

  -- ring B: the stored class card of both classes is dropped and rebuilt from the graph when next asked for
  delete from class_card where tenant_id = c.tenant_id and section in (c.section, p_section_t);

  select count(*) into made from prescription
   where child_id = c.id and week >= this_week and sheet_instance_id is not null;
  with gone as (
    delete from prescription
     where child_id = c.id and week >= this_week and sheet_instance_id is null and override_by is null
     returning 1
  ) select count(*) into withdrawn from gone;

  return jsonb_build_object('moved', true, 'prescriptions_withdrawn', withdrawn, 'papers_made', made);
end $$;

-- The function runs as its owner, as `say_taught` and `confirm_results` do, so the website needs no right to change `child`,
-- `class_card` or `prescription` itself: it may read the history and call the function, and nothing else. The coordinator
-- check is the website's, on the server (`moveChild`); the engine may also add to the ledger, as to every ledger.
-- (The roles of CI and live; absent on a plain copy.)
revoke all on function public.move_child(uuid, text, text, text, text, text) from public;
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on child_move to app_engine;
    grant execute on function public.move_child(uuid, text, text, text, text, text) to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on child_move to app_web;
    grant execute on function public.move_child(uuid, text, text, text, text, text) to app_web;
  end if;
end $$;

select internal.apply_conventions();
