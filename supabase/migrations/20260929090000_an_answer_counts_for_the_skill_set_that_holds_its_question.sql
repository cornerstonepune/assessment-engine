-- An answer counts for the skill set whose level holds its question, not for whatever skill set shares its
-- rung (ADR 0034).
--
-- `next_difficulty` found a skill set's answers by joining evidence to the skill set on `rung_code`. A rung is
-- the old ladder's step and can hold more than one operation: R9 is "3-digit ± with regrouping", while its
-- only skill set, ADD.3D.REG, practises addition — 3-digit subtraction's cases sit in SUB.2D.EXCH (Hard,
-- Advance) and SUB.3D.ZERO. So on 2026-09-22 Dhanvi's two "forgot to take one from the next column" mistakes
-- on R9 subtractions were the targets of her next *addition* paper, and subtraction was offered no paper.
--
-- A generated question already names its skill set (`item.skill_set_code`). An old paper's question does
-- not: `engine legacy place` measures its numbers against the team's taxonomy and writes here each skill set
-- and level whose cases it is one of (or the skill set on its rung that practises its skill, when its
-- numbers match no case). Derived, rewritten whole on every run, never edited by hand.
create table item_placement (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  item_id         uuid not null references item(id) on delete cascade,
  skill_set_code  text not null,
  difficulty      text check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance')),
  placed_by       text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  foreign key (tenant_id, skill_set_code) references skill_set(tenant_id, code),
  unique nulls not distinct (item_id, skill_set_code, difficulty)
);
create index item_placement_item_id_idx on item_placement (item_id);
create index item_placement_skill_set_idx on item_placement (tenant_id, skill_set_code);

select internal.apply_conventions();

-- A child's confirmed evidence on the questions a skill set holds — made for it, or placed in it — from
-- readings nothing has superseded. The one place the answer → skill set join is written.
-- ponytail: evidence that is not an answer to a question (no channel writes any yet) counts for no skill
-- set here; a teacher's observation will need its own route to a skill set when one is built.
create or replace function public.skill_set_evidence(p_child_id uuid, p_skill_set text)
returns setof evidence_event
language sql stable security definer set search_path = public as $$
  select e.*
  from evidence_event e
  join item_result r on r.id = e.item_result_id
  join capture c on c.id = r.capture_id
  join item i on i.id = r.item_id
  where e.child_id = p_child_id and e.confirmed_by is not null and c.superseded_by is null
    and (i.skill_set_code = p_skill_set
         or exists (select 1 from item_placement p where p.item_id = i.id and p.skill_set_code = p_skill_set))
$$;

create or replace function public.next_difficulty(p_child_id uuid, p_skill_set text)
returns table (difficulty text, rule text, targets text[])
language plpgsql stable security definer set search_path = public as $$
declare
  min_events numeric := coalesce((select value from threshold where key = 'state.min_events'), 3);
  promote    numeric := coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5);
  ord        text[]  := array['Easy', 'Medium', 'Hard', 'Advance'];
  answered integer; right_ integer; share numeric; at_ text; i integer; tg text[];
begin
  select count(*) filter (where a.correct is not null), count(*) filter (where a.correct)
    into answered, right_
  from (select e.item_result_id, bool_and(e.correct) as correct
          from skill_set_evidence(p_child_id, p_skill_set) e group by 1) a;

  if coalesce(answered, 0) < min_events then
    return query select null::text, 'band_default'::text, '{}'::text[];
    return;
  end if;
  share := right_::numeric / answered;

  select p.difficulty into at_ from prescription p
   where p.child_id = p_child_id and p.skill_set_code = p_skill_set and p.difficulty is not null
   order by p.created_at desc limit 1;
  at_ := coalesce(at_, 'Medium');
  i := coalesce(array_position(ord, at_), 2);

  select coalesce(array_agg(q.code order by q.n desc, q.code), '{}') into tg
  from (select m.code, count(*) as n
          from skill_set_evidence(p_child_id, p_skill_set) e, unnest(e.misconception_codes) as m(code)
         group by m.code having count(*) > 1
         order by n desc, m.code limit 3) q;

  if share >= promote then
    return query select ord[least(i + 1, 4)], 'from_state'::text, '{}'::text[];
  elsif share < demote then
    return query select ord[greatest(i - 1, 1)], 'from_state'::text, tg;
  else
    return query select at_, 'from_state'::text, tg;
  end if;
end $$;
