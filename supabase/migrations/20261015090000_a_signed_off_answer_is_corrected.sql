-- A signed-off answer can be corrected (Nimish, 2026-09-29: a paper signed off by mistake, two answers read as blank
-- that the child had written, 44 and 9). Until now a correction was refused once an answer was signed off, and the
-- only way out was to edit rows — which rule 4 forbids.
--
-- A correction is a new batch of evidence for that answer, never an edit: the batch it replaces stays in
-- `evidence_event` for ever, and the graph reads only an answer's latest batch. A sign-off writes one batch per
-- answer in one statement (so its rows share one `created_at`); a correction writes the next, stamped with
-- `clock_timestamp()` so it is later even inside the transaction that signed the paper off.
--
-- Everything the graph reads goes through `evidence_placed`, so the rule lives there once: `rebuild_child_skill_state`
-- and `next_difficulty` are unchanged. Evidence with no answer behind it (an educator's override) is never replaced.

create or replace view evidence_placed with (security_invoker = true) as
select e.*, coalesce(i.rung_code, e.rung_code) as placed_rung
from evidence_event e
left join item_result r on r.id = e.item_result_id
left join item i on i.id = r.item_id
where e.item_result_id is null
   or e.created_at = (select max(e2.created_at) from evidence_event e2 where e2.item_result_id = e.item_result_id);

-- What one marked answer is evidence of — the skills it counts for, right, wrong with its mistakes, or blank. The one
-- definition a sign-off and a correction share (it was inside `confirm_results`).
create or replace function public.answer_evidence(p_result_ids uuid[])
returns table (item_result_id uuid, tenant_id uuid, child_id uuid, rung_code text, observed_at timestamptz,
               skill text, correct boolean, codes text[])
language sql stable security definer set search_path = public as $$
  with pending as (
    select r.id, r.tenant_id, si.child_id, r.status, r.misconception_codes, i.rung_code, i.source, i.skill_codes,
           i.mistake_skills, coalesce(i.spec ->> 'skill', i.skill_codes[1]) as own_skill,
           coalesce((t.key ->> 'date')::timestamptz, c.created_at) as observed_at
    from item_result r
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    join item i on i.id = r.item_id
    where r.id = any(p_result_ids) and r.status in ('correct', 'wrong', 'blank')
  )
  select p.id, p.tenant_id, p.child_id, p.rung_code, p.observed_at, s.skill, true, '{}'::text[]
  from pending p
  cross join lateral unnest(
    case when p.source = 'generated' and cardinality(p.skill_codes) > 0 then p.skill_codes
         else array[p.own_skill] end) as s(skill)
  where p.status = 'correct'
  union all
  select p.id, p.tenant_id, p.child_id, p.rung_code, p.observed_at, coalesce(p.mistake_skills ->> m.code, p.own_skill),
         false, array_agg(m.code order by m.code)
  from pending p
  cross join lateral unnest(p.misconception_codes) as m(code)
  where p.status = 'wrong' and cardinality(p.misconception_codes) > 0
  group by p.id, p.tenant_id, p.child_id, p.rung_code, p.observed_at, coalesce(p.mistake_skills ->> m.code, p.own_skill)
  union all
  select p.id, p.tenant_id, p.child_id, p.rung_code, p.observed_at, p.own_skill,
         case p.status when 'wrong' then false else null end, p.misconception_codes
  from pending p
  where p.status = 'blank' or (p.status = 'wrong' and cardinality(p.misconception_codes) = 0)
$$;

create or replace function public.confirm_results(p_child_id uuid, p_by text, p_capture_id uuid default null)
returns integer
language plpgsql security definer set search_path = public as $$
declare n integer; ids uuid[];
begin
  select coalesce(array_agg(r.id), '{}') into ids
  from item_result r
  join capture c on c.id = r.capture_id
  join sheet_instance si on si.id = c.sheet_instance_id
  where si.child_id = p_child_id and r.state = 'candidate'
    and r.status in ('correct', 'wrong', 'blank')
    and (p_capture_id is null or r.capture_id = p_capture_id);
  with ev as (
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct,
                                misconception_codes, channel, item_result_id, observed_at, confirmed_by)
    select a.tenant_id, p_child_id, a.skill, a.rung_code, a.correct, a.codes, 'item', a.item_result_id,
           a.observed_at, p_by
    from answer_evidence(ids) a
    returning item_result_id
  )
  update item_result r set state = 'confirmed', confirmed_by = p_by, confirmed_at = now()
  where r.id in (select item_result_id from ev);
  get diagnostics n = row_count;
  perform rebuild_child_skill_state(p_child_id);
  return n;
end $$;

-- A signed-off answer, marked again from what a person says the child wrote: its next batch of evidence, in that
-- person's name, and the child's graph rebuilt. Returns the rows written; 0 when the answer is not signed off or
-- its new mark is not one evidence is written for.
create or replace function public.correct_signed_off(p_result_id uuid, p_by text)
returns integer
language plpgsql security definer set search_path = public as $$
declare n integer; kid uuid; at_ timestamptz := clock_timestamp();
begin
  select si.child_id into kid
  from item_result r
  join capture c on c.id = r.capture_id
  join sheet_instance si on si.id = c.sheet_instance_id
  where r.id = p_result_id and r.state = 'confirmed';
  if kid is null then
    return 0;
  end if;
  insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                              item_result_id, observed_at, confirmed_by, created_at, stored_at)
  select a.tenant_id, kid, a.skill, a.rung_code, a.correct, a.codes, 'item', a.item_result_id, a.observed_at,
         p_by, at_, at_
  from answer_evidence(array[p_result_id]) a;
  get diagnostics n = row_count;
  if n > 0 then
    update item_result set confirmed_by = p_by, confirmed_at = now() where id = p_result_id;
    perform rebuild_child_skill_state(kid);
  end if;
  return n;
end $$;
