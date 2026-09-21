-- A person confirms ONE paper, not every paper the child has ever sat.
--
-- `confirm_results(child, by)` took every candidate row a child had, wherever it came from. That
-- was right while the only screen was Child Growth, where a teacher is looking at the whole child.
-- The approval screen looks at one photograph: the teacher has just read eighteen answers on one
-- page, and confirming would have swept in answers from papers they have never seen. A signature
-- has to mean the person read the thing they signed.
--
-- The third parameter defaults to null, so every existing caller — `legacy.confirm`, the growth
-- screen, `resolve_result` — keeps confirming the whole child exactly as before. The 2-argument
-- function is dropped first: left in place, a 2-argument call would match both and Postgres would
-- refuse it as ambiguous.
drop function if exists public.confirm_results(uuid, text);

create or replace function public.confirm_results(p_child_id uuid, p_by text, p_capture_id uuid default null)
returns integer
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
      and (p_capture_id is null or r.capture_id = p_capture_id)
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
