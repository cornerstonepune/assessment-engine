-- A reading that has been superseded must not still be shaping a child's ladder.
--
-- `capture.superseded_by` is how a re-read replaces an earlier one without destroying it (rule 4),
-- and every screen already honours it. The graph did not: `rebuild_child_skill_state` and
-- `next_difficulty` read `evidence_event` straight, so evidence confirmed from a reading that has
-- since been replaced still counted. It mattered the day the whole corpus was re-read with the
-- transcriber that replaced the vision model: 218 answers confirmed from the old reader were
-- superseded, and every one of them was still in the ladder underneath the new ones.
--
-- Nothing is deleted and nothing is un-confirmed. The rows stay; the graph stops reading them.
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
           (select m.code
              from evidence_event e2
              left join item_result r2 on r2.id = e2.item_result_id
              left join capture c2 on c2.id = r2.capture_id,
                   unnest(e2.misconception_codes) as m(code)
             where e2.child_id = e.child_id and e2.skill_code = e.skill_code
               and e2.rung_code = e.rung_code and e2.confirmed_by is not null
               and (c2.id is null or c2.superseded_by is null)
             group by m.code having count(*) > 1
             order by count(*) desc, m.code limit 1)                            as repeating
    from evidence_event e
    left join item_result r on r.id = e.item_result_id
    left join capture c on c.id = r.capture_id
    where e.child_id = p_child_id and e.confirmed_by is not null
      and (c.id is null or c.superseded_by is null)
    group by e.tenant_id, e.child_id, e.skill_code, e.rung_code
  ) s;
  get diagnostics n = row_count;
  return n;
end $$;

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
  left join item_result r on r.id = e.item_result_id
  left join capture c on c.id = r.capture_id
  where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null
    and (c.id is null or c.superseded_by is null);

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
          join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code
          left join item_result r on r.id = e.item_result_id
          left join capture c on c.id = r.capture_id,
               unnest(e.misconception_codes) as m(code)
         where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null
           and (c.id is null or c.superseded_by is null)
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
