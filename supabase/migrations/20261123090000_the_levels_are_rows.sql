-- A skill's levels are rows (goals/b1-levels-are-rows.yaml, ADR 0084).
--
-- Nimish, 2026-10-20: "we need proper tables". A level lived inside three JSON objects on `skill_set`: its words and
-- rule in `difficulty`, its grade in `level_band` (or none, meaning the skill's own), its approval in `level_approved`.
-- None could be joined or keyed. Now each is a row of `skill_level`, its level a key into `difficulty`, its grade a key
-- into `grade`, its skill a key into `skill_set`, and its history its own (`skill_level_version`).
--
-- The blob is still what the website and the loader write, and what the readers not yet moved read, for one deploy
-- after the last reader moves. Until then the rows are kept equal to it by a trigger, whoever writes, and nobody else
-- writes them: so a moved reader and an old one can never disagree, and no paper, map or page changes on the day.
-- `engine levels check` compares the two level by level, and draws each level's questions from both on one seed.
--
-- What a level says is kept whole in `looks_like`: how its words split into a learning objective, what it looks like
-- and samples is Nimish's and Achal's to say (B3), so `learning_objective` waits empty until then.
--
-- Written to run twice.

create table if not exists skill_level (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  skill_code          text not null,
  difficulty          text not null,                 -- Easy, Medium, Hard, Advance: a row of `difficulty`
  grade               text not null,                 -- the grade that teaches this level: a row of `grade`
  learning_objective  text,                          -- empty until the split of a level's words is decided (B3)
  looks_like          text,                          -- the level's words, as a person reads and edits them
  rule                jsonb not null,                -- what only the generator reads: the level's rule, its target
  confirmed_by        text,                          -- who approved this level's questions …
  confirmed_at        timestamptz,                   -- … and when; a level is approved exactly when this is set
  version             integer not null default 1,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (tenant_id, skill_code, difficulty),
  foreign key (tenant_id, skill_code) references skill_set (tenant_id, code) on delete cascade on update cascade,
  foreign key (tenant_id, difficulty) references difficulty (tenant_id, code),
  foreign key (tenant_id, grade) references grade (tenant_id, code),
  constraint skill_level_rule_shape check (jsonb_typeof(rule) = 'object' and not rule ? 'words')
);

-- A level's earlier versions: what it said and asked until it was changed. Grade and approval are not versions of a
-- level (a move or an approval withdraws nothing, ADR 0073), and were not recorded per level before this table.
create table if not exists skill_level_version (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  skill_code          text not null,
  difficulty          text not null,
  version             integer not null,
  learning_objective  text,
  looks_like          text,
  rule                jsonb not null,
  valid_from          timestamptz not null,          -- when this version became current
  valid_to            timestamptz not null,          -- when it was replaced
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (tenant_id, skill_code, difficulty, version)
);

-- One skill's rows made equal to its blob: each level the blob has, with its words, its rule, its grade (named in
-- `level_band`, else its rung's) and its approval; a level the blob no longer has goes. Only a row that differs is
-- written, so a write that changes nothing about a level files no version of it.
create or replace function internal.skill_level_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from skill_level l
  where l.tenant_id = p_tenant and l.skill_code = p_code
    and not exists (select 1 from skill_set s where s.tenant_id = p_tenant and s.code = p_code and s.difficulty ? l.difficulty);
  insert into skill_level as l (tenant_id, skill_code, difficulty, grade, looks_like, rule, confirmed_by, confirmed_at)
  select s.tenant_id, s.code, e.key, coalesce(s.level_band ->> e.key, r.band), e.value ->> 'words', e.value - 'words',
         s.level_approved -> e.key ->> 'by',
         case when s.level_approved ? e.key
              then coalesce((s.level_approved -> e.key ->> 'at')::timestamptz, s.updated_at) end
  from skill_set s
  join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
  cross join jsonb_each(s.difficulty) e
  where s.tenant_id = p_tenant and s.code = p_code
  on conflict (tenant_id, skill_code, difficulty) do update
    set grade = excluded.grade, looks_like = excluded.looks_like, rule = excluded.rule,
        confirmed_by = excluded.confirmed_by, confirmed_at = excluded.confirmed_at
    where row(l.grade, l.looks_like, l.rule, l.confirmed_by, l.confirmed_at)
          is distinct from row(excluded.grade, excluded.looks_like, excluded.rule, excluded.confirmed_by, excluded.confirmed_at);
end $$;

create or replace function internal.skill_level_from_skill_set() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'UPDATE' and old.code is distinct from new.code then
    perform internal.skill_level_sync(old.tenant_id, old.code);
  end if;
  perform internal.skill_level_sync(new.tenant_id, new.code);
  return null;
end $$;

-- After the row is final: `skill_set_version_on_change` may have changed its approvals on the way.
drop trigger if exists skill_level_on_insert on skill_set;
create trigger skill_level_on_insert after insert on skill_set
  for each row execute function internal.skill_level_from_skill_set();
drop trigger if exists skill_level_on_update on skill_set;
create trigger skill_level_on_update after update on skill_set
  for each row when (
    row(old.code, old.rung_code, old.difficulty, old.level_band, old.level_approved)
    is distinct from row(new.code, new.rung_code, new.difficulty, new.level_band, new.level_approved))
  execute function internal.skill_level_from_skill_set();

-- A level not moved to another grade is its skill's grade, which is its rung's: when a rung's grade moves, so do they.
create or replace function internal.skill_level_from_rung() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_level_sync(s.tenant_id, s.code)
  from skill_set s where s.tenant_id = new.tenant_id and s.rung_code = new.code;
  return null;
end $$;

drop trigger if exists skill_level_on_rung on rung;
create trigger skill_level_on_rung after update of band on rung
  for each row when (old.band is distinct from new.band) execute function internal.skill_level_from_rung();

-- A change to what a level says or asks files its previous version, and only its own.
create or replace function internal.skill_level_version_on_change() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if row(new.learning_objective, new.looks_like, new.rule) is distinct from row(old.learning_objective, old.looks_like, old.rule) then
    insert into skill_level_version (tenant_id, skill_code, difficulty, version, learning_objective, looks_like, rule,
                                     valid_from, valid_to)
    values (old.tenant_id, old.skill_code, old.difficulty, old.version, old.learning_objective, old.looks_like, old.rule,
            old.updated_at, now());
    new.version := old.version + 1;
  end if;
  return new;
end $$;

-- Named to sort before touch_updated_at (both BEFORE UPDATE, run alphabetically), so valid_from reads the old row's own
-- updated_at, as `skill_set_version_on_change` does.
drop trigger if exists skill_level_version_on_change on skill_level;
create trigger skill_level_version_on_change before update on skill_level
  for each row execute function internal.skill_level_version_on_change();

-- The levels as they are today, from the blob; and the history the skill kept, carried onto each level, once.
do $$
declare first_time boolean := not exists (select 1 from skill_level);
begin
  perform internal.skill_level_sync(s.tenant_id, s.code) from skill_set s;
  if not first_time then
    return;
  end if;
  -- Each level's states through the skill's versions, then today's: a run of versions in which the level said and
  -- asked the same thing is one version of the level. Every state but today's is filed; today's row carries the count.
  with states as (
    select v.tenant_id, v.code, e.key as difficulty, e.value ->> 'words' as looks_like, e.value - 'words' as rule,
           v.version as skill_version, v.valid_from, v.valid_to
    from skill_set_version v cross join jsonb_each(v.difficulty) e
    union all
    select l.tenant_id, l.skill_code, l.difficulty, l.looks_like, l.rule, s.version, s.updated_at, null
    from skill_level l join skill_set s on s.tenant_id = l.tenant_id and s.code = l.skill_code
  ), marked as (
    select *, case when row(looks_like, rule) is distinct from row(
                lag(looks_like) over w, lag(rule) over w) then 1 else 0 end as starts
    from states window w as (partition by tenant_id, code, difficulty order by skill_version)
  ), runs as (
    select *, sum(starts) over (partition by tenant_id, code, difficulty order by skill_version) as level_version
    from marked
  ), versions as (
    select tenant_id, code, difficulty, level_version, min(valid_from) as valid_from,
           (array_agg(looks_like order by skill_version))[1] as looks_like,
           (array_agg(rule order by skill_version))[1] as rule,
           bool_or(valid_to is null) as current
    from runs group by tenant_id, code, difficulty, level_version
  ), filed as (
    insert into skill_level_version (tenant_id, skill_code, difficulty, version, looks_like, rule, valid_from, valid_to)
    select v.tenant_id, v.code, v.difficulty, v.level_version, v.looks_like, v.rule, v.valid_from,
           coalesce(lead(v.valid_from) over (partition by v.tenant_id, v.code, v.difficulty order by v.level_version), now())
    from versions v where not v.current
    returning 1
  )
  update skill_level l set version = v.level_version
  from versions v
  where v.current and v.tenant_id = l.tenant_id and v.code = l.skill_code and v.difficulty = l.difficulty
    and l.version is distinct from v.level_version;
end $$;

-- A skill's levels as the blob held them, {level: {words, …rule}}, built from the rows: what a reader that wants the
-- whole rule of every level reads, so a moved reader is handed the same object the blob gave it.
create or replace function public.skill_levels(tenant uuid, skill text) returns jsonb
language sql stable set search_path = public as $$
  select coalesce(jsonb_object_agg(l.difficulty,
           case when l.looks_like is null then l.rule else l.rule || jsonb_build_object('words', l.looks_like) end),
         '{}'::jsonb)
  from skill_level l where l.tenant_id = $1 and l.skill_code = $2
$$;

select internal.apply_conventions();

-- The rows are the blob's mirror until the writers move: only the trigger above writes them, as their owner.
do $$
begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    revoke insert, update, delete, truncate on skill_level, skill_level_version from app_web, app_engine;
  end if;
end $$;
