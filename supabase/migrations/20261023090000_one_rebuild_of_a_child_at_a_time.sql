-- One rebuild of a child's states at a time (goals/p2-live-recovers.yaml). The function deletes the child's
-- rows and writes them again; two calls at once (an educator signing a paper off while a deploy marks every answer
-- again) each deleted only what was there before both began, and the second insert failed on the first's rows with a
-- duplicate key. A lock per child, held to the end of the transaction, puts the second after the first. The body is
-- 20261002090000's, unchanged but for the lock.

create or replace function public.rebuild_child_skill_state(p_child_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  min_events numeric := coalesce((select value from threshold where key = 'state.min_events'), 3);
  min_obs    numeric := coalesce((select value from threshold where key = 'state.min_observers'), 2);
  promote    numeric := coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5);
  n integer;
begin
  -- one rebuild of a child at a time: two at once each deleted what the other had not yet written, and the second
  -- insert failed on the first's rows (code review, 2026-09-30)
  perform pg_advisory_xact_lock(hashtext('rebuild_child_skill_state'), hashtext(p_child_id::text));
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
    select e.tenant_id, e.child_id, e.skill_code, e.placed_rung as rung_code,
           count(*) filter (where e.correct is not null)                        as n_events,
           count(*) filter (where e.correct)                                    as n_correct,
           (count(*) filter (where e.correct))::numeric
             / nullif(count(*) filter (where e.correct is not null), 0)          as share,
           count(distinct coalesce(r.capture_id::text, e.id::text))             as observers,
           max(e.observed_at)                                                   as last_seen,
           (select m.code
              from evidence_placed e2
              left join item_result r2 on r2.id = e2.item_result_id
              left join capture c2 on c2.id = r2.capture_id,
                   unnest(e2.misconception_codes) as m(code)
             where e2.child_id = e.child_id and e2.skill_code = e.skill_code
               and e2.placed_rung = e.placed_rung and e2.confirmed_by is not null
               and (c2.id is null or c2.superseded_by is null)
             group by m.code having count(*) > 1
             order by count(*) desc, m.code limit 1)                            as repeating
    from evidence_placed e
    left join item_result r on r.id = e.item_result_id
    left join capture c on c.id = r.capture_id
    where e.child_id = p_child_id and e.confirmed_by is not null
      and (c.id is null or c.superseded_by is null)
    group by e.tenant_id, e.child_id, e.skill_code, e.placed_rung
  ) s;
  get diagnostics n = row_count;
  return n;
end $function$;
