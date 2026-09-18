-- The graph rule lives in the database so the engine CLI and the web app run the same code.
-- Every number is a threshold row (CLAUDE.md rule 1); nothing here is tuned by a deploy.
--
-- Six states, per child × skill × rung, from confirmed evidence only (rule 4):
--   not_enough_yet   fewer than state.min_events answers
--   patterned_error  one misconception matched more than once
--   emerging         under next_sheet.demote_below correct
--   practising       under next_sheet.promote_at, or fewer than state.min_observers papers
--   secure           at or above promote_at across enough papers
--   stretch_ready    secure with twice min_events behind it — enough to move up
-- ADR 0006 records this as provisional until Aseem has read a term of maps.

create or replace function public.rebuild_child_skill_state(p_child_id uuid) returns integer
language plpgsql security definer set search_path = public as $$
declare
  min_events numeric := coalesce((select value from threshold where key = 'state.min_events'), 3);
  min_obs    numeric := coalesce((select value from threshold where key = 'state.min_observers'), 2);
  promote    numeric := coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5);
  n integer;
begin
  delete from child_skill_state where child_id = p_child_id;
  insert into child_skill_state
    (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, repeating_misconception, last_seen)
  select s.tenant_id, s.child_id, s.skill_code, s.rung_code,
         case when s.n_events < min_events                     then 'not_enough_yet'
              when s.repeating is not null                     then 'patterned_error'
              when s.share < demote                            then 'emerging'
              when s.share < promote or s.observers < min_obs  then 'practising'
              when s.n_events >= 2 * min_events                then 'stretch_ready'
              else 'secure' end,
         s.n_events, s.n_correct, s.repeating, s.last_seen
  from (
    select e.tenant_id, e.child_id, e.skill_code, e.rung_code,
           count(*) filter (where e.correct is not null)                        as n_events,
           count(*) filter (where e.correct)                                    as n_correct,
           (count(*) filter (where e.correct))::numeric
             / nullif(count(*) filter (where e.correct is not null), 0)          as share,
           count(distinct coalesce(r.capture_id::text, e.id::text))             as observers,
           max(e.observed_at)                                                   as last_seen,
           (select m.code from evidence_event e2, unnest(e2.misconception_codes) as m(code)
             where e2.child_id = e.child_id and e2.skill_code = e.skill_code
               and e2.rung_code = e.rung_code and e2.confirmed_by is not null
             group by m.code having count(*) > 1
             order by count(*) desc, m.code limit 1)                            as repeating
    from evidence_event e
    left join item_result r on r.id = e.item_result_id
    where e.child_id = p_child_id and e.confirmed_by is not null
    group by e.tenant_id, e.child_id, e.skill_code, e.rung_code
  ) s;
  get diagnostics n = row_count;
  return n;
end $$;

-- The next-sheet rule (SPEC §5): promote at promote_at, demote below demote_below, else hold.
-- Returns difficulty null with rule band_default when there is not enough to go on.
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
  select count(*) filter (where e.correct is not null), count(*) filter (where e.correct)
    into answered, right_
  from evidence_event e
  join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code
  where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null;

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
          from evidence_event e
          join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code,
               unnest(e.misconception_codes) as m(code)
         where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null
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

-- A person confirms a child's candidate results: each becomes an evidence_event and the
-- child's states are rebuilt. Only the machine-markable statuses are taken; unreadable and
-- needs_teacher rows wait for resolve_result.
create or replace function public.confirm_results(p_child_id uuid, p_by text) returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with pending as (
    select r.id, r.tenant_id, r.status, r.misconception_codes, i.rung_code, i.spec, i.skill_codes,
           coalesce((t.key ->> 'date')::timestamptz, c.created_at) as observed_at
    from item_result r
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    join item i on i.id = r.item_id
    where si.child_id = p_child_id and r.state = 'candidate'
      and r.status in ('correct', 'wrong', 'blank')
  ), ev as (
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct,
                                misconception_codes, channel, item_result_id, observed_at, confirmed_by)
    select tenant_id, p_child_id, coalesce(spec ->> 'skill', skill_codes[1]), rung_code,
           case status when 'correct' then true when 'wrong' then false else null end,
           misconception_codes, 'item', id, observed_at, p_by
    from pending
    returning item_result_id
  )
  update item_result r set state = 'confirmed', confirmed_by = p_by, confirmed_at = now()
  from ev where r.id = ev.item_result_id;
  get diagnostics n = row_count;
  perform rebuild_child_skill_state(p_child_id);
  return n;
end $$;

-- A person settles one row the machine could not: what the child's answer was, in the three
-- signals the school keeps apart (blank / wrong / correct), optionally naming the mistake.
create or replace function public.resolve_result(p_result_id uuid, p_status text, p_codes text[], p_by text)
returns void language plpgsql security definer set search_path = public as $$
declare child uuid;
begin
  if p_status not in ('correct', 'wrong', 'blank') then
    raise exception 'resolve_result: status must be correct, wrong or blank, not %', p_status;
  end if;
  update item_result set status = p_status, misconception_codes = coalesce(p_codes, '{}')
   where id = p_result_id and state = 'candidate';
  select si.child_id into child from item_result r
    join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
   where r.id = p_result_id;
  if child is null then raise exception 'resolve_result: no candidate result %', p_result_id; end if;
  perform confirm_results(child, p_by);
end $$;
