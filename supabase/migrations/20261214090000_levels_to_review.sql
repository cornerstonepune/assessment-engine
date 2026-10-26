-- Levels to review: when most of a grade or class is secure at a level, the level may be too easy
-- (goals/cal_levels_to_review.yaml). Nimish, 2026-10-26: "If 8 out of 10 people in the class are able to solve the
-- advanced level for that particular grade or school, then that's not actually advanced." His decisions: the system only
-- suggests and never changes a level, the threshold is 80 percent, the minimum is 8 children.
--
--   * Three thresholds, as rows (rule 1): the share (calibration.too_easy_share), the fewest children before any
--     suggestion (calibration.min_children), and how far the numbers must move before a looked-at suggestion is asked
--     again (calibration.review_again_children). The seed holds them too (supabase/seed/thresholds.json); written here so
--     live has them from the deploy, before the next `engine load`. A row already there is not touched.
--   * "Secure" is the graph's own rule, not a second one. The case that turned a child's answers on a skill into a state
--     lived inside `rebuild_child_skill_state`; it is now `internal.graph_state_of`, which that function and the new view
--     both call. `rebuild_child_skill_state` gives every child the very state it gave: only where the case is written moved.
--   * `child_level_state`: the same rule on a child's answers at one level of one skill (ring B, a view: a pure function of
--     the confirmed evidence, so nothing to rebuild). A blank is an answer that was given and is not a success: the child
--     was assessed, and the rule counts only right and wrong in its share.
--   * `calibration_review`: "I've looked at this", one row each time, never changed or removed (rule 4).
--   * `level_calibration`: for each skill and level, for a grade and for one class, the children assessed, the children
--     secure, and the verdict: too_few (under the minimum: nothing is suggested), review (the share is at or over the
--     threshold) or fine. Counted by code; a model never says a number.
--
-- Additive: nothing existing is read differently. Written to run twice.

insert into threshold (tenant_id, key, value, unit, description)
select t.id, v.key, v.value, v.unit, v.description
from tenant t,
     (values
       ('calibration.too_easy_share', 0.8, 'proportion',
        'A level is suggested for review when at least this share of the children assessed at it are secure'),
       ('calibration.min_children', 8, 'children',
        'Fewest children assessed at a level before it is judged at all'),
       ('calibration.review_again_children', 2, 'children',
        'A suggestion marked looked-at comes back when the children assessed, or the children secure, moved by this many')
     ) v (key, value, unit, description)
on conflict (tenant_id, key) do nothing;

-- The graph's rule, once. The words are 20261023090000's case, unchanged; its four numbers are the thresholds it read.
create or replace function internal.graph_state_of(
  p_tenant uuid, p_n_events numeric, p_share numeric, p_observers numeric, p_repeating text
) returns text
language sql stable set search_path = public as $$
  select case when p_n_events < t.min_events                       then 'not_enough_yet'
              when p_repeating is not null                         then 'patterned_error'
              when p_share < t.demote                              then 'emerging'
              when p_share < t.promote or p_observers < t.min_obs  then 'practising'
              when p_n_events >= 2 * t.min_events                  then 'stretch_ready'
              else 'secure' end
  from (select
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.min_events'), 3)        as min_events,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'state.min_observers'), 2)     as min_obs,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'next_sheet.promote_at'), 0.8) as promote,
          coalesce((select value from threshold where tenant_id = p_tenant and key = 'next_sheet.demote_below'), 0.5) as demote
       ) t
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
    (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct, repeating_misconception, last_seen)
  select s.tenant_id, s.child_id, s.skill_code, s.rung_code,
         internal.graph_state_of(s.tenant_id, s.n_events, s.share, s.observers, s.repeating),
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

-- A child's state at one level of one skill: the graph's rule on the confirmed answers of questions made for that level.
create or replace view child_level_state with (security_invoker = true) as
select s.tenant_id, s.child_id, s.skill_code, s.difficulty,
       internal.graph_state_of(s.tenant_id, s.n_events, s.share, s.observers, s.repeating) as state,
       s.n_events, s.n_correct, s.last_seen
from (
  select e.tenant_id, e.child_id, i.skill_set_code as skill_code, i.difficulty,
         count(*) filter (where e.correct is not null)                          as n_events,
         count(*) filter (where e.correct)                                      as n_correct,
         (count(*) filter (where e.correct))::numeric
           / nullif(count(*) filter (where e.correct is not null), 0)            as share,
         count(distinct coalesce(r.capture_id::text, e.id::text))               as observers,
         max(e.observed_at)                                                     as last_seen,
         (select m.code
            from evidence_placed e2
            join item_result r2 on r2.id = e2.item_result_id
            join item i2 on i2.id = r2.item_id
            left join capture c2 on c2.id = r2.capture_id,
                 unnest(e2.misconception_codes) as m(code)
           where e2.child_id = e.child_id and e2.confirmed_by is not null
             and i2.skill_set_code = i.skill_set_code and i2.difficulty = i.difficulty
             and (c2.id is null or c2.superseded_by is null)
           group by m.code having count(*) > 1
           order by count(*) desc, m.code limit 1)                              as repeating
  from evidence_placed e
  join item_result r on r.id = e.item_result_id
  join item i on i.id = r.item_id
  left join capture c on c.id = r.capture_id
  where e.confirmed_by is not null
    and (c.id is null or c.superseded_by is null)
    and i.skill_set_code is not null and i.difficulty is not null
  group by e.tenant_id, e.child_id, i.skill_set_code, i.difficulty
) s;

-- "I've looked at this": a row each time, with the counts it was looked at on, never changed (rule 4).
create table if not exists calibration_review (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  skill_code   text not null,
  difficulty   text not null,
  scope_kind   text not null check (scope_kind in ('grade', 'class')),
  scope_value  text not null check (btrim(scope_value) <> ''),
  assessed     integer not null check (assessed >= 0),
  secure       integer not null check (secure >= 0),
  reviewed_by  text not null check (btrim(reviewed_by) <> ''),
  reviewed_at  timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  foreign key (tenant_id, skill_code) references skill (tenant_id, code) on update cascade,
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code)
);
create index if not exists calibration_review_level_idx
  on calibration_review (tenant_id, skill_code, difficulty, scope_kind, scope_value, reviewed_at desc);

drop trigger if exists calibration_review_append_only on calibration_review;
create trigger calibration_review_append_only before update or delete on calibration_review
  for each statement execute function internal.forbid_change();

-- For every skill and level, for each grade and each class: how many children have been assessed at it, how many are
-- secure there (a state the school's rows call enough and not needing work), and what that says.
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

select internal.apply_conventions();
