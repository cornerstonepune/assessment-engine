-- A confirmed answer is evidence for every skill its question uses (ADR 0023, step 8c).
--
-- Until now one answer made one evidence row, on `coalesce(spec ->> 'skill', skill_codes[1])` — so a
-- two-step budget problem answered right counted for "word problems" alone, and one answered with "added
-- the costs but never took them from the budget" counted against word problems too. Now:
--   * a right answer: one row per skill the question uses (`item.skill_codes`, read from the question —
--     ADR 0030); a question from an old paper still has the one skill a person gave it;
--   * a wrong answer with named mistakes: one row per skill those mistakes charge (`item.mistake_skills`,
--     step 8b), each row carrying the mistakes that charge it;
--   * an unexplained wrong answer, or a blank: one row on the question's own skill. An unexplained one
--     keeps no mistake code, which is how `engine bank unclassified` finds it.
--
-- `next_difficulty` counted evidence rows, so a four-skill question answered right would have weighed four
-- times a one-skill one. It now counts answers: an answer is right when every row it made is right.

create or replace function public.confirm_results(p_child_id uuid, p_by text, p_capture_id uuid default null)
returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with pending as (
    select r.id, r.tenant_id, r.status, r.misconception_codes, i.rung_code, i.source, i.skill_codes,
           i.mistake_skills, coalesce(i.spec ->> 'skill', i.skill_codes[1]) as own_skill,
           coalesce((t.key ->> 'date')::timestamptz, c.created_at) as observed_at
    from item_result r
    join capture c on c.id = r.capture_id
    join sheet_instance si on si.id = c.sheet_instance_id
    join sheet_template t on t.id = si.sheet_template_id
    join item i on i.id = r.item_id
    where si.child_id = p_child_id and r.state = 'candidate'
      and r.status in ('correct', 'wrong', 'blank')
      and (p_capture_id is null or r.capture_id = p_capture_id)
  ), rows_ as (
    select p.id, p.tenant_id, p.rung_code, p.observed_at, s.skill, true as correct, '{}'::text[] as codes
    from pending p
    cross join lateral unnest(
      case when p.source = 'generated' and cardinality(p.skill_codes) > 0 then p.skill_codes
           else array[p.own_skill] end) as s(skill)
    where p.status = 'correct'
    union all
    select p.id, p.tenant_id, p.rung_code, p.observed_at, coalesce(p.mistake_skills ->> m.code, p.own_skill),
           false, array_agg(m.code order by m.code)
    from pending p
    cross join lateral unnest(p.misconception_codes) as m(code)
    where p.status = 'wrong' and cardinality(p.misconception_codes) > 0
    group by p.id, p.tenant_id, p.rung_code, p.observed_at, coalesce(p.mistake_skills ->> m.code, p.own_skill)
    union all
    select p.id, p.tenant_id, p.rung_code, p.observed_at, p.own_skill,
           case p.status when 'wrong' then false else null end, p.misconception_codes
    from pending p
    where p.status = 'blank' or (p.status = 'wrong' and cardinality(p.misconception_codes) = 0)
  ), ev as (
    insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct,
                                misconception_codes, channel, item_result_id, observed_at, confirmed_by)
    select tenant_id, p_child_id, skill, rung_code, correct, codes, 'item', id, observed_at, p_by
    from rows_
    returning item_result_id
  )
  update item_result r set state = 'confirmed', confirmed_by = p_by, confirmed_at = now()
  where r.id in (select item_result_id from ev);
  get diagnostics n = row_count;
  perform rebuild_child_skill_state(p_child_id);
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
  select count(*) filter (where a.correct is not null), count(*) filter (where a.correct)
    into answered, right_
  from (
    select coalesce(e.item_result_id, e.id) as answer, bool_and(e.correct) as correct
    from evidence_event e
    join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code
    left join item_result r on r.id = e.item_result_id
    left join capture c on c.id = r.capture_id
    where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null
      and (c.id is null or c.superseded_by is null)
    group by 1
  ) a;

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
