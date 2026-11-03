-- A child's state reads their recent answers at the level they work on, and the next paper's level reads their last
-- two papers at that level alone (goals/gr1-state-from-recent-evidence.yaml). Nimish, 2026-11-03, from the
-- learning-science review (cornerstonepune/teacher-os research/council-2026-11-03/learning-scientist.md §1):
--   * `next_difficulty` pooled every answer at every level, all time: 20 Easy right and 4 Medium wrong was 0.83, a move
--     up. It now reads the last `next_sheet.papers` papers at the child's current level only.
--   * a repeating mistake was any code seen twice, ever, and never cleared. It now counts only while it shows in
--     `state.repeat_min` of a level's last `state.window_answers` answers, and clears after
--     `state.repeat_clears_after` right answers on later papers.
--   * the share was all-time. It is now the last `state.window_answers` answers at the level.
--   * "observers" counted papers (each answer with no paper counted as one). It is now school days
--     (`state.min_days`), and for evidence that names who saw it, distinct adults (`state.min_adults`).
--   * secure needs `state.secure_min_answers` answers at the level, on `state.min_days` days, the latest day at
--     `next_sheet.promote_at`; until a paper `state.recheck_days` later at that level or a harder one reaches it too,
--     it is the new state `secure_to_recheck` ("secure, to re-check"), not counted as secure.
--   * `stretch_ready` was volume (twice min_events). It is now re-checked secure with a harder level above; re-checked
--     at the hardest level is `secure`.
-- Nimish's answers that day: a skill's one state (child_skill_state) is its state at the level of the child's latest
-- answers, and the row says which level; the provisional secure is a state row; days for every kind, adults only for
-- evidence naming who saw it.
--
-- Ring A is not touched (rule 4): no evidence row is written, changed or removed. Ring B is what changes, at the next
-- rebuild (`engine graph`). Written to run twice.

-- The rule's numbers, as rows (rule 1). `state.min_observers` counted papers as observers and goes.
insert into threshold (tenant_id, key, value, unit, description)
select t.id, v.key, v.value, v.unit, v.description
from tenant t,
     (values
       ('state.window_answers', 10, 'answers',
        'A level''s state reads only this many of its latest answers that are right or wrong'),
       ('state.secure_min_answers', 6, 'answers', 'Fewest answers at a level, in its window, before it can be secure'),
       ('state.min_days', 2, 'days', 'Different school days a level''s window must span before it can be secure'),
       ('state.min_adults', 2, 'adults',
        'Different adults who saw it, for evidence that names them (observed, voice, project), before it can be secure'),
       ('state.repeat_min', 2, 'answers',
        'A mistake repeats while it shows in at least this many of a level''s window; the next paper targets it then'),
       ('state.repeat_clears_after', 3, 'answers',
        'Right answers on papers after a mistake''s last showing that clear it'),
       ('state.recheck_days', 14, 'days',
        'A secure level is re-checked by a paper at least this many days later, at it or harder, that reaches promote_at'),
       ('next_sheet.papers', 2, 'papers', 'The latest papers at the current level the next paper''s level is read from')
     ) v (key, value, unit, description)
on conflict (tenant_id, key) do nothing;

delete from threshold where key = 'state.min_observers';
update threshold set description = 'At-level share right over the last next_sheet.papers papers to move up a level; '
  || 'also what a level''s window and its latest day must reach to be secure'
where key = 'next_sheet.promote_at';

-- The new state, between practising and secure, and the school's states for every school there now or added later.
-- Practising's reason now covers too few answers or days, not the share alone: "Right 10 of 10 — not yet four in five
-- right" was what a paper said of a child right on every answer of one day.
create or replace function internal.school_states(p_tenant uuid) returns void
language plpgsql as $$
begin
  insert into state_colour (tenant_id, code, ord, words, count_words)
  select p_tenant, v.code, v.ord, v.words, v.count_words
  from (values
    ('red', 0, 'needs help', 'needs help'),
    ('amber', 1, 'practising', 'practising'),
    ('green', 2, 'got it', 'secure'),
    ('grey', 3, 'not enough yet', 'too few answers')
  ) v (code, ord, words, count_words)
  on conflict (tenant_id, code) do nothing;

  insert into child_state (tenant_id, code, ord, words, colour, needs_work, enough, severity, move_up, nearly,
                           card_group, why)
  select p_tenant, v.code, v.ord, v.words, v.colour, v.needs_work, v.enough, v.severity, v.move_up, v.nearly,
         v.card_group, v.why
  from (values
    ('patterned_error', 0, 'repeating mistake', 'red', true, true, 1, false, false, 'reteach',
     'the same mistake more than once'),
    ('emerging', 1, 'under half right', 'red', true, true, 2, false, false, 'emerging',
     'fewer than {next_sheet.demote_below} right'),
    ('practising', 2, 'practising', 'amber', true, true, 3, false, true, 'practising',
     'not yet {next_sheet.promote_at} right on enough answers and days'),
    ('secure_to_recheck', 3, 'secure, to re-check', 'amber', true, true, 4, false, true, 'practising',
     '{next_sheet.promote_at} right — to check again on a later paper'),
    ('secure', 4, 'secure', 'green', false, true, 5, false, false, 'secure',
     '{next_sheet.promote_at} right — a step up'),
    ('stretch_ready', 5, 'ready to move up', 'green', false, true, 5, true, false, 'move_up', 'ready to move up'),
    ('not_enough_yet', 6, 'not enough yet', 'grey', false, false, 4, false, false, 'not_enough_yet', null)
  ) v (code, ord, words, colour, needs_work, enough, severity, move_up, nearly, card_group, why)
  on conflict (tenant_id, code) do update set
    ord = excluded.ord, enough = excluded.enough, severity = excluded.severity, move_up = excluded.move_up,
    nearly = excluded.nearly, card_group = excluded.card_group, why = excluded.why;
end $$;

select internal.school_states(id) from tenant;

-- The level a skill's one state is at: the level of the child's latest answers on it (Nimish, 2026-11-03).
alter table child_skill_state add column if not exists difficulty text;
alter table child_skill_state drop constraint if exists child_skill_state_tenant_id_difficulty_fkey;
alter table child_skill_state add constraint child_skill_state_tenant_id_difficulty_fkey
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code);

-- Every signed-off answer the graph reads, with the level its question was made at, the school day it was sat and its
-- place on its paper. A paper is its sheet; an answer on no sheet is a paper of its own day. The place decides which of a
-- paper's answers a window keeps when it ends inside the paper: the last questions asked, never an id's chance order.
create or replace view graph_answer with (security_invoker = true) as
select e.id, e.tenant_id, e.child_id, e.skill_code, e.placed_rung as rung_code, i.skill_set_code, i.difficulty,
       d.ord as level_ord, e.correct, e.misconception_codes, e.observed_at, ev.seen_by,
       coalesce(e.item_result_id, e.id) as answer, array_position(t.item_ids, r.item_id) as pos,
       (e.observed_at at time zone coalesce(z.value #>> '{}', 'UTC'))::date as day,
       coalesce(c.sheet_instance_id::text, c.id::text,
                ((e.observed_at at time zone coalesce(z.value #>> '{}', 'UTC'))::date)::text) as paper
from evidence_placed e
join evidence_event ev on ev.id = e.id  -- who saw it: C2's column, which evidence_placed does not carry
left join item_result r on r.id = e.item_result_id
left join item i on i.id = r.item_id
left join capture c on c.id = r.capture_id
left join sheet_instance si on si.id = c.sheet_instance_id
left join sheet_template t on t.id = si.sheet_template_id
left join difficulty d on d.tenant_id = e.tenant_id and d.code = i.difficulty
left join config z on z.tenant_id = e.tenant_id and z.key = 'school.time_zone'
where e.confirmed_by is not null
  and (c.id is null or c.superseded_by is null);

-- One child's (or, with none named, every child's) window at each level of each unit: a registry skill on its rung
-- (scope 'skill', what child_skill_state holds) or the skill a question was made for (scope 'set', one row per answer,
-- what Levels to review reads). Counts, shares, days and adults over the level's last state.window_answers answers that
-- are right or wrong; the mistake repeating in them, unless right answers on later papers cleared it; whether a paper
-- state.recheck_days after a passing day in the window, at the level or harder, also passed; whether a harder level is
-- there to move to.
create or replace function public.graph_level_window(p_child uuid default null)
returns table (scope text, tenant_id uuid, child_id uuid, unit text, rung_code text, difficulty text, level_ord int,
               n_events int, n_correct int, share numeric, days int, adults int, latest_share numeric,
               repeating text, rechecked boolean, harder boolean, latest_at timestamptz)
language sql stable set search_path = public as $$
  with th as (  -- every school's numbers; one with no row yet reads the seed's
    select t.id as tenant_id,
           coalesce((select value from threshold where tenant_id = t.id and key = 'state.window_answers'), 10)     as win,
           coalesce((select value from threshold where tenant_id = t.id and key = 'state.repeat_min'), 2)          as repeat_min,
           coalesce((select value from threshold where tenant_id = t.id and key = 'state.repeat_clears_after'), 3) as clears,
           coalesce((select value from threshold where tenant_id = t.id and key = 'state.recheck_days'), 14)       as recheck,
           coalesce((select value from threshold where tenant_id = t.id and key = 'next_sheet.promote_at'), 0.8)   as promote
    from tenant t
  ), a as (
    select 'skill'::text as scope, g.tenant_id, g.child_id, g.skill_code as unit, g.rung_code, g.difficulty,
           g.level_ord, g.correct, g.misconception_codes, g.observed_at, g.seen_by, g.day, g.pos, g.id
    from graph_answer g
    where p_child is null or g.child_id = p_child
    union all
    select * from (
      select distinct on (g.answer) 'set'::text, g.tenant_id, g.child_id, g.skill_set_code, null::text, g.difficulty,
             g.level_ord, g.correct, g.misconception_codes, g.observed_at, g.seen_by, g.day, g.pos, g.id
      from graph_answer g
      where g.skill_set_code is not null and (p_child is null or g.child_id = p_child)
      order by g.answer, g.id
    ) s
  ), r as (
    select a.*, a.correct is not null and row_number() over (
             partition by a.scope, a.child_id, a.unit, a.rung_code, a.difficulty, a.correct is null
             order by a.observed_at desc, a.pos desc nulls last, a.id desc) <= th.win as w
    from a join th on th.tenant_id = a.tenant_id
  ), lv as (
    select r.scope, r.tenant_id, r.child_id, r.unit, r.rung_code, r.difficulty, r.level_ord,
           (count(*) filter (where r.w))::int                                         as n_events,
           (count(*) filter (where r.w and r.correct))::int                           as n_correct,
           (count(*) filter (where r.w and r.correct))::numeric
             / nullif(count(*) filter (where r.w), 0)                                 as share,
           (count(distinct r.day) filter (where r.w))::int                            as days,
           (count(distinct r.seen_by) filter (where r.w))::int                        as adults,
           max(r.day) filter (where r.w)                                              as latest_day,
           max(r.observed_at)                                                         as latest_at
    from r group by 1, 2, 3, 4, 5, 6, 7
  ), sat as (  -- each day's share at each level: a passing day reaches promote_at
    select a.scope, a.child_id, a.unit, a.rung_code, a.difficulty, a.level_ord, a.day,
           avg(a.correct::int) >= max(th.promote) as passed
    from a join th on th.tenant_id = a.tenant_id
    where a.correct is not null
    group by 1, 2, 3, 4, 5, 6, 7
  )
  select lv.scope, lv.tenant_id, lv.child_id, lv.unit, lv.rung_code, lv.difficulty, lv.level_ord,
         lv.n_events, lv.n_correct, lv.share, lv.days, lv.adults,
         (select avg(r.correct::int) from r
           where r.w and r.scope = lv.scope and r.child_id = lv.child_id and r.unit = lv.unit
             and r.rung_code is not distinct from lv.rung_code and r.difficulty is not distinct from lv.difficulty
             and r.day = lv.latest_day)                                               as latest_share,
         (select m.code
            from r, unnest(r.misconception_codes) as m(code)
           where r.w and r.scope = lv.scope and r.child_id = lv.child_id and r.unit = lv.unit
             and r.rung_code is not distinct from lv.rung_code and r.difficulty is not distinct from lv.difficulty
           group by m.code
          having count(*) >= th.repeat_min
             and (select count(*) from r r2
                   where r2.w and r2.correct and r2.scope = lv.scope and r2.child_id = lv.child_id
                     and r2.unit = lv.unit and r2.rung_code is not distinct from lv.rung_code
                     and r2.difficulty is not distinct from lv.difficulty
                     and r2.observed_at > max(r.observed_at)) < th.clears
           order by count(*) desc, m.code limit 1)                                    as repeating,
         exists (
           select 1 from sat s1 join sat s2 on s2.scope = s1.scope and s2.child_id = s1.child_id and s2.unit = s1.unit
                                         and s2.rung_code is not distinct from s1.rung_code
           where s1.scope = lv.scope and s1.child_id = lv.child_id and s1.unit = lv.unit
             and s1.rung_code is not distinct from lv.rung_code and s1.difficulty is not distinct from lv.difficulty
             and s1.passed and s2.passed and s2.day >= s1.day + th.recheck::int
             and s1.day in (select r.day from r where r.w and r.scope = lv.scope and r.child_id = lv.child_id
                              and r.unit = lv.unit and r.rung_code is not distinct from lv.rung_code
                              and r.difficulty is not distinct from lv.difficulty)
             and (s2.difficulty is not distinct from lv.difficulty or s2.level_ord > lv.level_ord))  as rechecked,
         exists (select 1 from difficulty d where d.tenant_id = lv.tenant_id and d.ord > lv.level_ord)  as harder,
         lv.latest_at
  from lv join th on th.tenant_id = lv.tenant_id
$$;

-- The graph's rule, once: a level's window to its state. Its numbers are the thresholds it reads.
drop view if exists level_calibration;
drop view if exists child_level_state;
drop function if exists public.graph_state_of(uuid, numeric, numeric, numeric, text);

create or replace function public.graph_state_of(
  p_tenant uuid, p_n_events numeric, p_share numeric, p_days numeric, p_adults numeric, p_repeating text,
  p_latest_share numeric, p_rechecked boolean, p_harder boolean
) returns text
language sql stable set search_path = public as $$
  select case when p_n_events < t.min_events                                      then 'not_enough_yet'
              when p_repeating is not null                                        then 'patterned_error'
              when p_share < t.demote                                             then 'emerging'
              when p_share < t.promote or p_n_events < t.secure_min or p_days < t.min_days
                   or p_latest_share < t.promote
                   or (p_adults > 0 and p_adults < t.min_adults)                  then 'practising'
              when not p_rechecked                                                then 'secure_to_recheck'
              when p_harder                                                       then 'stretch_ready'
              else 'secure' end
  from (select
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.min_events'), 3)          as min_events,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.secure_min_answers'), 6)  as secure_min,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.min_days'), 2)            as min_days,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.min_adults'), 2)          as min_adults,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'next_sheet.promote_at'), 0.8)   as promote,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'next_sheet.demote_below'), 0.5) as demote
       ) t
$$;

-- A child's graph (or, with none named, every child's): one row per registry skill on its rung, at the level of the
-- child's latest answers on it, with the window's share, days and re-check that decided it. What
-- `rebuild_child_skill_state` writes, `engine live data` compares the table with, and a parent report says why by.
drop function if exists public.graph_skill_states(uuid);
create function public.graph_skill_states(p_child uuid default null)
returns table (tenant_id uuid, child_id uuid, skill_code text, rung_code text, difficulty text, state text,
               n_events int, n_correct int, repeating_misconception text, last_seen timestamptz,
               share numeric, days int, latest_share numeric, rechecked boolean)
language sql stable set search_path = public as $$
  select l.tenant_id, l.child_id, l.unit, l.rung_code, l.difficulty,
         public.graph_state_of(l.tenant_id, l.n_events, l.share, l.days, l.adults, l.repeating, l.latest_share,
                               l.rechecked, l.harder),
         l.n_events, l.n_correct, l.repeating, l.last_seen, l.share, l.days, l.latest_share, l.rechecked
  from (
    select distinct on (w.child_id, w.unit, w.rung_code) w.*,
           max(w.latest_at) over (partition by w.child_id, w.unit, w.rung_code) as last_seen
    from public.graph_level_window(p_child) w
    where w.scope = 'skill'
    order by w.child_id, w.unit, w.rung_code, w.latest_at desc, w.level_ord desc nulls last
  ) l
$$;

create or replace function public.rebuild_child_skill_state(p_child_id uuid)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  n integer;
begin
  -- one rebuild of a child at a time: two at once each deleted what the other had not yet written, and the second
  -- insert failed on the first's rows (code review, 2026-09-30)
  perform pg_advisory_xact_lock(hashtext('rebuild_child_skill_state'), hashtext(p_child_id::text));
  delete from child_skill_state where child_id = p_child_id;
  insert into child_skill_state
    (tenant_id, child_id, skill_code, rung_code, difficulty, state, n_events, n_correct, repeating_misconception,
     last_seen)
  select g.tenant_id, g.child_id, g.skill_code, g.rung_code, g.difficulty, g.state, g.n_events, g.n_correct,
         g.repeating_misconception, g.last_seen
  from public.graph_skill_states(p_child_id) g;
  get diagnostics n = row_count;
  return n;
end $function$;

-- A child's state at one level of one skill: the same rule on the answers to questions made for that level.
create or replace view child_level_state with (security_invoker = true) as
select w.tenant_id, w.child_id, w.unit as skill_code, w.difficulty,
       public.graph_state_of(w.tenant_id, w.n_events, w.share, w.days, w.adults, w.repeating, w.latest_share,
                             w.rechecked, w.harder) as state,
       w.n_events, w.n_correct, w.latest_at as last_seen
from public.graph_level_window() w
where w.scope = 'set' and w.difficulty is not null;

-- Levels to review, as 20261216090000 made it, over the view above.
create or replace view level_calibration with (security_invoker = true) as
with kid as (
  select l.tenant_id, l.child_id, l.skill_code, l.difficulty, c.section, c.band,
         (st.enough and not st.needs_work) as is_secure
  from child_level_state l
  join child c on c.id = l.child_id and c.active
  join child_state st on st.tenant_id = l.tenant_id and st.code = l.state
), counted as (
  select tenant_id, 'class'::text as scope_kind, section as scope_value, class_band(tenant_id, section) as grade,
         skill_code, difficulty, count(*)::int as assessed, (count(*) filter (where is_secure))::int as secure
  from kid group by tenant_id, section, skill_code, difficulty
  union all
  select tenant_id, 'grade', band, band, skill_code, difficulty, count(*)::int, (count(*) filter (where is_secure))::int
  from kid group by tenant_id, band, skill_code, difficulty
), th as (
  select tenant_id,
         max(value) filter (where key = 'calibration.too_easy_share')          as share,
         max(value) filter (where key = 'calibration.min_children')            as min_children,
         max(value) filter (where key = 'calibration.review_again_children')   as again
  from threshold group by tenant_id
)
select n.tenant_id, n.scope_kind, n.scope_value, n.grade, n.skill_code, n.difficulty, n.assessed, n.secure,
       th.min_children::int as min_children, th.share as share_needed,
       case when n.assessed < th.min_children                   then 'too_few'
            when n.secure::numeric / n.assessed >= th.share     then 'review'
            else 'fine' end as verdict,
       r.reviewed_at as looked_at, r.reviewed_by as looked_by
from counted n
join th on th.tenant_id = n.tenant_id
left join lateral (
  select v.reviewed_at, v.reviewed_by, v.assessed, v.secure
  from calibration_review v
  where v.tenant_id = n.tenant_id and v.skill_code = n.skill_code and v.difficulty = n.difficulty
    and v.scope_kind = n.scope_kind and v.scope_value = n.scope_value
  order by v.reviewed_at desc, v.id limit 1
) r on abs(n.assessed - r.assessed) < th.again and abs(n.secure - r.secure) < th.again
where th.share is not null and th.min_children is not null and th.again is not null;

-- The next paper's level: up one when the last next_sheet.papers papers at the child's current level reach
-- promote_at, down one under demote_below, kept between. The current level is the last one prescribed, else the
-- level of the latest answers on the skill, else `level.usual`. Too few answers on the skill at all: the grade's
-- starting level. Too few at the current level (moved up, not yet sat): stays there. The mistakes it targets are
-- those repeating in the same papers.
create or replace function public.next_difficulty(p_child_id uuid, p_skill_set text)
returns table (difficulty text, rule text, targets text[])
language plpgsql stable security definer rows 1 set search_path = public as $$
declare
  tenant_    uuid    := (select tenant_id from child where id = p_child_id);
  min_events numeric := coalesce((select value from threshold where tenant_id = tenant_ and key = 'state.min_events'), 3);
  promote    numeric := coalesce((select value from threshold where tenant_id = tenant_ and key = 'next_sheet.promote_at'), 0.8);
  demote     numeric := coalesce((select value from threshold where tenant_id = tenant_ and key = 'next_sheet.demote_below'), 0.5);
  papers     integer := coalesce((select value from threshold where tenant_id = tenant_ and key = 'next_sheet.papers'), 2);
  repeat_min numeric := coalesce((select value from threshold where tenant_id = tenant_ and key = 'state.repeat_min'), 2);
  ord        text[]  := array(select d.code from difficulty d where d.tenant_id = tenant_ order by d.ord);
  usual      text    := (select c.value #>> '{}' from config c where c.tenant_id = tenant_ and c.key = 'level.usual');
  total integer; answered integer; right_ integer; share numeric; at_ text; i integer; tg text[];
begin
  -- every answer on the skill's rung, right or wrong, one row each (an answer counts once however many registry skills
  -- it used), at any level or none: too few, and nothing says where the child is. A paper made before levels (the
  -- historical papers, N3) names none, so it never sets the next level, but it is answers: such a child stays at their
  -- current level, as a child just moved up does (rehearsal run 119: the grade's start instead reset 60 levels the
  -- school had already set).
  select count(distinct g.answer) into total
  from graph_answer g join skill s on s.tenant_id = g.tenant_id and s.rung_code = g.rung_code
  where g.child_id = p_child_id and s.code = p_skill_set and g.correct is not null;
  if total < min_events then
    return query select null::text, 'band_default'::text, '{}'::text[];
    return;
  end if;

  select p.difficulty into at_ from prescription p
   where p.child_id = p_child_id and p.skill_set_code = p_skill_set and p.difficulty is not null
   order by p.created_at desc limit 1;
  at_ := coalesce(at_, (select g.difficulty
                          from graph_answer g join skill s on s.tenant_id = g.tenant_id and s.rung_code = g.rung_code
                         where g.child_id = p_child_id and s.code = p_skill_set and g.difficulty is not null
                         order by g.observed_at desc, g.level_ord desc limit 1), usual);
  i := coalesce(array_position(ord, at_), array_position(ord, usual));

  with ans as (  -- the answers at the current level, one row each
    select g.answer, max(g.paper) as paper, max(g.observed_at) as observed_at, bool_and(g.correct) as correct,
           max(g.misconception_codes) as codes
    from graph_answer g join skill s on s.tenant_id = g.tenant_id and s.rung_code = g.rung_code
    where g.child_id = p_child_id and s.code = p_skill_set and g.correct is not null and g.difficulty = at_
    group by g.answer
  ), last_ as (  -- of them, those on the latest papers
    select a.* from ans a
    where a.paper in (select a2.paper from ans a2 group by a2.paper order by max(a2.observed_at) desc limit papers)
  )
  select (select count(*) from last_), (select count(*) from last_ where correct),
         coalesce((select array_agg(q.code order by q.n desc, q.code)
                   from (select m.code, count(*) as n from last_, unnest(last_.codes) as m(code)
                          group by m.code having count(*) >= repeat_min
                          order by n desc, m.code limit 3) q), '{}')
    into answered, right_, tg;

  if answered < min_events then
    return query select at_, 'from_state'::text, tg;
    return;
  end if;
  share := right_::numeric / answered;
  if share >= promote then
    return query select ord[least(i + 1, cardinality(ord))], 'from_state'::text, '{}'::text[];
  elsif share < demote then
    return query select ord[greatest(i - 1, 1)], 'from_state'::text, tg;
  else
    return query select at_, 'from_state'::text, tg;
  end if;
end $$;

-- The roles of CI and live read the rule and its views (absent on a plain copy).
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant execute on function public.graph_state_of(uuid, numeric, numeric, numeric, numeric, text, numeric, boolean,
                                                    boolean) to app_engine;
    grant execute on function public.graph_level_window(uuid), public.graph_skill_states(uuid) to app_engine;
    grant select on graph_answer, child_level_state, level_calibration to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant execute on function public.graph_state_of(uuid, numeric, numeric, numeric, numeric, text, numeric, boolean,
                                                    boolean) to app_web;
    grant execute on function public.graph_level_window(uuid) to app_web;  -- child_level_state, read as the website
    grant select on graph_answer, child_level_state, level_calibration to app_web;
  end if;
end $$;

select internal.apply_conventions();
