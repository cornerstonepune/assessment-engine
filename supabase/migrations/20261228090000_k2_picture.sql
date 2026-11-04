-- A K2 child's picture per skill from confirmed voice notes (goals/m1-02-k2-picture.yaml, task M1-02; design in
-- docs/notes/m1-02-k2-picture.md). The school's rule (D-008, D-051, D-052; the orchestrator's answers under D-047):
--   * a skill is secure only after the child is named (individual entry) at level 3 on two different school
--     days, and a yes comes at least 14 days after the first of those; "the rest did as expected" at level 3 may be
--     that re-check, never opens secure on its own and never moves a state down;
--   * once a skill is secure (or secure, to re-check), a later named lower mark re-opens it and resets the clock: secure
--     needs a fresh cycle counting only marks after it; before that, a lower mark changes only what is shown (the
--     orchestrator, D-047, unverified with the school);
--   * a child seen only in "the rest" lines is observed with too little to go on (not_enough_yet); a child not
--     mentioned has no row, never "not secure".
-- The rule's numbers are rows per grade (`observed_rule`), and how much each way of entering a child counts is rows per
-- grade, kind and entry mode (`observed_weight`); nothing about weight is on an evidence row. One adult is enough for
-- K2 in the pilot (the written rule's `state.min_adults` 2 is not read here).
--
-- Additive only: three new tables, their rows, the functions. No existing table, column, row or function is changed;
-- the written graph (`graph_answer`, `rebuild_child_skill_state`, `child_skill_state`) reads `kind = 'written'` alone
-- and is untouched, so every state written tests give is what it was. `child_observed_state` is ring B: a pure
-- function of ring A, emptied and rebuilt by `engine graph`, so nothing here refuses TRUNCATE.
--
-- Written to run twice.

create table if not exists observed_rule (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  grade_code    text not null,
  secure_level  int not null check (secure_level between 0 and 3),  -- the level a named day must reach
  secure_days   int not null check (secure_days > 0),           -- different school days named at that level
  recheck_days  int not null check (recheck_days >= 0),         -- a re-check at least this long after the first
  min_adults    int not null check (min_adults > 0),            -- different adults who named it
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (tenant_id, grade_code),
  foreign key (tenant_id, grade_code) references grade (tenant_id, code)
);

create table if not exists observed_weight (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  grade_code    text not null,
  kind          text not null,
  entry_mode    text not null,
  opens_secure  boolean not null,  -- its day counts toward the named days secure needs
  rechecks      boolean not null,  -- it may be the re-check
  lowers        boolean not null,  -- a lower mark from it re-opens a secure skill and decides practising or emerging
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (tenant_id, grade_code, kind, entry_mode),
  foreign key (tenant_id, grade_code) references grade (tenant_id, code),
  foreign key (tenant_id, kind) references evidence_kind (tenant_id, code),
  foreign key (tenant_id, entry_mode) references observation_entry_mode (tenant_id, code)
);

create table if not exists child_observed_state (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references tenant(id) on delete cascade,
  child_id         uuid not null references child(id) on delete cascade,
  skill_code       text not null,
  grade_code       text not null,
  state            text not null,
  named_days       int not null,   -- school days named at the secure level
  adults           int not null,   -- adults who named it at the secure level
  first_named_yes  date,
  rechecked_on     date,           -- the first day a re-check reached the level, at least recheck_days after
  last_seen        timestamptz not null,
  computed_at      timestamptz not null default now(),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (tenant_id, child_id, skill_code, grade_code),
  foreign key (tenant_id, grade_code) references grade (tenant_id, code),
  foreign key (tenant_id, state) references child_state (tenant_id, code)
);
create index if not exists child_observed_state_child_idx on child_observed_state (child_id);

-- K2's rule and weights, for every school there now and any added later. They name a new school's grades, kinds and
-- entry modes, made by its triggers school_vocabulary, evidence_vocabulary and voice_vocabulary; PostgreSQL fires a
-- table's triggers in the order of their names, so this one is named to come after all three.
create or replace function internal.observed_rules(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into observed_rule (tenant_id, grade_code, secure_level, secure_days, recheck_days, min_adults)
  values (p_tenant, 'K2', 3, 2, 14, 1)
  on conflict (tenant_id, grade_code) do nothing;
  insert into observed_weight (tenant_id, grade_code, kind, entry_mode, opens_secure, rechecks, lowers)
  values (p_tenant, 'K2', 'observed', 'individual', true, true, true),
         (p_tenant, 'K2', 'observed', 'group_as_expected', false, true, false)
  on conflict (tenant_id, grade_code, kind, entry_mode) do nothing;
end $$;

create or replace function internal.observed_rules_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.observed_rules(new.id);
  return new;
end $$;

drop trigger if exists voice_vocabulary_then_observed_rules on tenant;
create trigger voice_vocabulary_then_observed_rules after insert on tenant
  for each row execute function internal.observed_rules_on_new_school();

select internal.observed_rules(id) from tenant;

-- The rule, once: one child's (or, with none named, every child's) state per skill per grade, from confirmed evidence
-- that names its observation, weighted by its grade's rows. Evidence of a corrected observation no longer counts; a
-- school day is the date in `school.time_zone`; a grade with no rule rows gives no state.
--
-- The level is the one the educator's outcome showed (`activity_observation.reached_level`), read as stored, never
-- worked back from a mark: the level-to-mark setting may change and the rule does not move with it. The mark decides
-- only what a building skill shows (emerging when the latest named mark is not_yet), the word the educator sees.
-- A small state machine over each child-skill's marks in time order (at one moment, the secure level first and a lower
-- one after it, so the lower decides):
--   building          -> secure_to_recheck  named at the secure level on secure_days different days, by min_adults
--   secure_to_recheck -> secure             a yes that may re-check, recheck_days or more after the cycle's first
--   secure_to_recheck or secure -> re-opened (shown practising) on a named lower mark: the cycle starts again, its
--                     first yes, its days and its re-check counting only marks after that lower mark
--   building          a lower mark changes only what is shown: emerging if the latest named mark is not_yet
-- A mark whose weight may not lower (the rest did as expected) never re-opens and never decides what is shown.
create or replace function public.graph_observed_states(p_child uuid default null)
returns table (tenant_id uuid, child_id uuid, skill_code text, grade_code text, state text, named_days int,
               adults int, first_named_yes date, rechecked_on date, last_seen timestamptz)
language plpgsql stable set search_path = public as $$
#variable_conflict use_column
declare
  m record;
  unit text := null;
  phase text;          -- building, to_recheck, secure
  reopened boolean;
  yes_days date[];
  who text[];
  latest text;
  named boolean;
  goal record;
begin
  for m in
    select e.tenant_id, e.child_id, e.skill_code, k.grade_code, e.mark, e.seen_by, e.observed_at,
           (e.observed_at at time zone coalesce(z.value #>> '{}', 'UTC'))::date as day,
           w.opens_secure, w.rechecks, w.lowers, o.reached_level >= r.secure_level as reached, r.secure_days, r.recheck_days, r.min_adults,
           concat_ws('|', e.child_id, e.skill_code, k.grade_code) as unit
    from evidence_event e
    join activity_observation o on o.id = e.observation_id and o.tenant_id = e.tenant_id
    join school_class k on k.id = o.class_id
    join observed_weight w on w.tenant_id = e.tenant_id and w.grade_code = k.grade_code and w.kind = e.kind
                          and w.entry_mode = o.entry_mode
    join observed_rule r on r.tenant_id = e.tenant_id and r.grade_code = k.grade_code
    left join config z on z.tenant_id = e.tenant_id and z.key = 'school.time_zone'
    where e.confirmed_by is not null and o.reached_level is not null
      and (p_child is null or e.child_id = p_child)
      and not exists (select 1 from activity_observation c where c.supersedes = o.id)
    order by e.child_id, e.skill_code, k.grade_code, e.observed_at, o.reached_level < r.secure_level, e.id
  loop
    if unit is distinct from m.unit then
      if unit is not null then
        return query select goal.tenant_id, goal.child_id, goal.skill_code, goal.grade_code,
          case when not named then 'not_enough_yet' when phase = 'secure' then 'secure'
               when phase = 'to_recheck' then 'secure_to_recheck' when reopened then 'practising'
               when latest = 'not_yet' then 'emerging' else 'practising' end,
          cardinality(yes_days), cardinality(who), goal.first_yes, goal.rechecked, goal.last_seen;
      end if;
      unit := m.unit; phase := 'building'; reopened := false; yes_days := '{}'; who := '{}'; latest := null;
      named := false;
      select m.tenant_id, m.child_id, m.skill_code, m.grade_code, null::date as first_yes, null::date as rechecked,
             m.observed_at as last_seen into goal;
    end if;
    goal.last_seen := m.observed_at;
    if m.lowers then
      named := true;
      latest := m.mark;
      if not m.reached and phase in ('to_recheck', 'secure') then  -- re-opened: the clock starts again
        phase := 'building'; reopened := true; yes_days := '{}'; who := '{}';
        goal.first_yes := null; goal.rechecked := null;
      end if;
    end if;
    if m.reached then
      if m.rechecks and goal.first_yes is not null and m.day >= goal.first_yes + m.recheck_days then
        goal.rechecked := coalesce(goal.rechecked, m.day);
      end if;
      if m.opens_secure then
        goal.first_yes := coalesce(goal.first_yes, m.day);
        if not m.day = any (yes_days) then yes_days := yes_days || m.day; end if;
        if not m.seen_by = any (who) then who := who || m.seen_by; end if;
      end if;
    end if;
    if phase <> 'secure' and cardinality(yes_days) >= m.secure_days and cardinality(who) >= m.min_adults then
      phase := case when goal.rechecked is not null then 'secure' else 'to_recheck' end;
      reopened := false;
    end if;
  end loop;
  if unit is not null then
    return query select goal.tenant_id, goal.child_id, goal.skill_code, goal.grade_code,
      case when not named then 'not_enough_yet' when phase = 'secure' then 'secure'
           when phase = 'to_recheck' then 'secure_to_recheck' when reopened then 'practising'
           when latest = 'not_yet' then 'emerging' else 'practising' end,
      cardinality(yes_days), cardinality(who), goal.first_yes, goal.rechecked, goal.last_seen;
  end if;
end $$;

create or replace function public.rebuild_child_observed_state(p_child_id uuid)
returns integer
language plpgsql security definer set search_path = public as $$
declare
  n integer;
begin
  -- one rebuild of a child at a time, as rebuild_child_skill_state
  perform pg_advisory_xact_lock(hashtext('rebuild_child_observed_state'), hashtext(p_child_id::text));
  delete from child_observed_state where child_id = p_child_id;
  insert into child_observed_state (tenant_id, child_id, skill_code, grade_code, state, named_days, adults,
                                    first_named_yes, rechecked_on, last_seen)
  select g.tenant_id, g.child_id, g.skill_code, g.grade_code, g.state, g.named_days, g.adults, g.first_named_yes,
         g.rechecked_on, g.last_seen
  from public.graph_observed_states(p_child_id) g;
  get diagnostics n = row_count;
  return n;
end $$;

-- Both services read; only the rebuild (security definer) writes the picture. The default privileges of
-- 20261021090000 give the engine every privilege on a new public table, DELETE among them; they are taken back.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select on observed_rule, observed_weight, child_observed_state to app_engine;
    revoke insert, update, delete, truncate on observed_rule, observed_weight, child_observed_state from app_engine;
    grant execute on function public.graph_observed_states(uuid), public.rebuild_child_observed_state(uuid)
      to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on observed_rule, observed_weight, child_observed_state to app_web;
    revoke insert, update, delete, truncate on observed_rule, observed_weight, child_observed_state from app_web;
  end if;
end $$;

select internal.apply_conventions();
