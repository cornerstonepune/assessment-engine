-- The four levels are read from `difficulty` everywhere (goals/b0c-levels-from-the-table.yaml, ADR 0084).
--
-- Nimish, 2026-10-20: "we need proper tables". B0a made the levels a table; the engine, the website and
-- `next_difficulty` still wrote their names, order and worksheet letters again. Now:
-- - a level's letter in a worksheet code (R5-M03) is a column of its row, set by the seed (vocabulary.json): each level's
--   initial, as every code has been made, and one level's alone in a school, so two levels never print the same code. Not
--   derived from the name: a level called "Expert" beside Easy takes a letter of its own;
-- - the level a paper is at when nothing says otherwise is the config row `level.usual` ("Medium"), made here for
--   every school because `next_difficulty` reads it before any load runs; a load keeps it as config.json says;
-- - `next_difficulty` moves a child up or down the school's own order, so a level added is a level a child can reach.
-- Nothing a child is given changes: tests/test_levels.py runs the rule as it was, case by case. Written to run twice.

alter table difficulty add column if not exists letter text;
update difficulty set letter = upper(left(code, 1)) where letter is null;
alter table difficulty drop constraint if exists difficulty_tenant_id_letter_key;
alter table difficulty add constraint difficulty_tenant_id_letter_key unique (tenant_id, letter);

insert into config (tenant_id, key, value, description)
select t.id, 'level.usual', '"Medium"'::jsonb,
       'The level a paper is at when nothing says otherwise: a child with no level yet, a grade with no starting level, '
       || 'a topic''s default assessment, a skill chosen on the maker.'
from tenant t
on conflict (tenant_id, key) do nothing;

create or replace function public.next_difficulty(p_child_id uuid, p_skill_set text)
returns table (difficulty text, rule text, targets text[])
language plpgsql stable security definer rows 1 set search_path = public as $$
declare
  tenant_    uuid    := (select tenant_id from child where id = p_child_id);
  min_events numeric := coalesce((select value from threshold where key = 'state.min_events'), 3);
  promote    numeric := coalesce((select value from threshold where key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where key = 'next_sheet.demote_below'), 0.5);
  ord        text[]  := array(select d.code from difficulty d where d.tenant_id = tenant_ order by d.ord);
  usual      text    := (select c.value #>> '{}' from config c where c.tenant_id = tenant_ and c.key = 'level.usual');
  answered integer; right_ integer; share numeric; at_ text; i integer; tg text[];
begin
  select count(*) filter (where a.correct is not null), count(*) filter (where a.correct)
    into answered, right_
  from (
    select coalesce(e.item_result_id, e.id) as answer, bool_and(e.correct) as correct
    from evidence_placed e
    join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.placed_rung
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
  at_ := coalesce(at_, usual);
  i := coalesce(array_position(ord, at_), array_position(ord, usual));

  select coalesce(array_agg(q.code order by q.n desc, q.code), '{}') into tg
  from (select m.code, count(*) as n
          from evidence_placed e
          join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.placed_rung
          left join item_result r on r.id = e.item_result_id
          left join capture c on c.id = r.capture_id,
               unnest(e.misconception_codes) as m(code)
         where e.child_id = p_child_id and s.code = p_skill_set and e.confirmed_by is not null
           and (c.id is null or c.superseded_by is null)
         group by m.code having count(*) > 1
         order by n desc, m.code limit 3) q;

  if share >= promote then
    return query select ord[least(i + 1, cardinality(ord))], 'from_state'::text, '{}'::text[];
  elsif share < demote then
    return query select ord[greatest(i - 1, 1)], 'from_state'::text, tg;
  else
    return query select at_, 'from_state'::text, tg;
  end if;
end $$;
