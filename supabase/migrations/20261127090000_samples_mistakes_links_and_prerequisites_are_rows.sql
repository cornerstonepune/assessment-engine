-- A level's samples, a skill's mistakes, its registry skills and what comes before it are rows
-- (goals/b3-samples-mistakes-prerequisites.yaml, ADR 0092).
--
-- Nimish, 2026-10-20: "we need proper tables". Four things a skill names lived where the database never checked them:
-- the examples inside a level's words and a card kind's `kind`, the mistake codes in `skill_set.misconception_codes`,
-- the registry skills in its rung's `skill_codes`, and what comes before it nowhere at all. Now each is a row, and each
-- code a key: a skill that names a mistake, a registry skill, a level or a skill that is no row is refused.
--
-- The lists on `skill_set` and `rung` are still what the website, the loader and the engine write (`spec.apply_computed`
-- and `_store` add mistakes). Until those writers move, the rows are kept equal to the lists by triggers, whoever
-- writes, and nobody else writes them, as B1 keeps `skill_level` (ADR 0087). `engine links check` compares the two.
-- Prerequisites are new, so they are the rows themselves: drafted from the seed by `engine load`, then a person's.
--
-- Written to run twice.

-- A level's samples: the examples its words give after their colon, and each card kind's examples of it.
create table if not exists skill_level_sample (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references tenant(id) on delete cascade,
  skill_code       text not null,
  difficulty       text not null,
  question_format  text,                             -- the card kind it is an example of; none for one in the words
  ord              integer not null,                 -- its place among its level's samples from the same source
  sample           text not null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  foreign key (tenant_id, skill_code, difficulty) references skill_level (tenant_id, skill_code, difficulty)
    on delete cascade on update cascade,
  foreign key (tenant_id, question_format) references question_format (tenant_id, code) on delete cascade on update cascade,
  constraint skill_level_sample_written check (btrim(sample) <> '' and ord > 0)
);
create unique index if not exists skill_level_sample_one_place
  on skill_level_sample (tenant_id, skill_code, difficulty, coalesce(question_format, ''), ord);

-- The mistakes a skill watches for: one row for each row of `misconception` its codes name (a code is one mistake,
-- written once for each operation it shows in, as evidence names it by code alone).
create table if not exists skill_mistake (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid not null references tenant(id) on delete cascade,
  skill_code          text not null,
  misconception_code  text not null,
  op                  text not null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (tenant_id, skill_code, misconception_code, op),
  foreign key (tenant_id, skill_code) references skill_set (tenant_id, code) on delete cascade on update cascade,
  foreign key (tenant_id, misconception_code, op) references misconception (tenant_id, code, op) on update cascade
);

-- The registry skills a skill covers: its rung's `skill_codes`.
create table if not exists skill_registry_link (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  skill_code      text not null,
  registry_skill  text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (tenant_id, skill_code, registry_skill),
  foreign key (tenant_id, skill_code) references skill_set (tenant_id, code) on delete cascade on update cascade,
  foreign key (tenant_id, registry_skill) references skill (tenant_id, code) on update cascade
);

-- What comes before a skill: another skill a child meets first.
create table if not exists skill_prerequisite (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenant(id) on delete cascade,
  skill_code   text not null,
  before_code  text not null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, skill_code, before_code),
  foreign key (tenant_id, skill_code) references skill_set (tenant_id, code) on delete cascade on update cascade,
  foreign key (tenant_id, before_code) references skill_set (tenant_id, code) on delete cascade on update cascade,
  constraint skill_prerequisite_not_itself check (skill_code <> before_code)
);

-- No skill comes before itself, however long the way round.
create or replace function internal.skill_prerequisite_no_circle() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (
    with recursive before(code) as (
      select new.before_code
      union
      select p.before_code from skill_prerequisite p join before b on p.tenant_id = new.tenant_id and p.skill_code = b.code
    ) select 1 from before where code = new.skill_code
  ) then
    raise exception 'skill % would come before itself through %', new.skill_code, new.before_code
      using errcode = 'check_violation';
  end if;
  return null;
end $$;

drop trigger if exists skill_prerequisite_no_circle on skill_prerequisite;
create constraint trigger skill_prerequisite_no_circle after insert or update on skill_prerequisite
  for each row execute function internal.skill_prerequisite_no_circle();

-- A level's examples, as its words give them (decision B3-1): the text after the words' last colon, to the end of that
-- sentence, cut at ", " and "; "; numbers written in a row ("5, 10, 15, 20, □") are one example; a piece is a sample
-- when it is written in signs, a number sentence with no word but a remainder's "r". A piece in words stays words only.
create or replace function internal.level_samples(words text) returns table (ord integer, sample text)
language plpgsql immutable as $$
declare
  tail text;
  piece text;
  pieces text[] := '{}';
  n integer := 0;
begin
  if words is null or position(':' in words) = 0 then
    return;
  end if;
  tail := regexp_replace(words, '^.*:', '');
  tail := regexp_replace(tail, '\.\s+[A-Z].*$', '');
  tail := regexp_replace(btrim(tail), '\.$', '');
  foreach piece in array regexp_split_to_array(tail, ',\s+|;\s+') loop
    piece := btrim(piece);
    continue when piece = '';
    if piece ~ '^[0-9□]+$' and cardinality(pieces) > 0 and pieces[cardinality(pieces)] ~ '^[0-9□, ]+$' then
      pieces[cardinality(pieces)] := pieces[cardinality(pieces)] || ', ' || piece;
    else
      pieces := pieces || piece;
    end if;
  end loop;
  foreach piece in array pieces loop
    if regexp_replace(piece, '([0-9]) r ([0-9])', '\1 \2', 'g') !~ '[A-Za-z]' and piece ~ '[-+−×÷=≈<>○□]' then
      n := n + 1;
      ord := n;
      sample := piece;
      return next;
    end if;
  end loop;
end $$;

-- One skill's samples made equal to its levels' words and its card kinds' examples.
create or replace function internal.skill_level_sample_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from skill_level_sample where tenant_id = p_tenant and skill_code = p_code;
  insert into skill_level_sample (tenant_id, skill_code, difficulty, question_format, ord, sample)
  select l.tenant_id, l.skill_code, l.difficulty, null, x.ord, x.sample
  from skill_level l cross join lateral internal.level_samples(l.looks_like) x
  where l.tenant_id = p_tenant and l.skill_code = p_code
  union all
  select f.tenant_id, f.skill_set_code, e.key, f.code, x.ord::integer, x.sample
  from question_format f
  cross join jsonb_each(case when jsonb_typeof(f.kind -> 'examples') = 'object' then f.kind -> 'examples' else '{}' end) e
  cross join jsonb_array_elements_text(e.value) with ordinality x(sample, ord)
  join skill_level l on l.tenant_id = f.tenant_id and l.skill_code = f.skill_set_code and l.difficulty = e.key
  where f.tenant_id = p_tenant and f.skill_set_code = p_code;
end $$;

create or replace function internal.skill_level_sample_from_level() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_level_sample_sync(new.tenant_id, new.skill_code);
  return null;
end $$;

drop trigger if exists skill_level_sample_on_level on skill_level;
create trigger skill_level_sample_on_level after insert or update of looks_like on skill_level
  for each row execute function internal.skill_level_sample_from_level();

create or replace function internal.skill_level_sample_from_card() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if tg_op in ('UPDATE', 'DELETE') then
    perform internal.skill_level_sample_sync(old.tenant_id, old.skill_set_code);
  end if;
  if tg_op in ('INSERT', 'UPDATE') then
    perform internal.skill_level_sample_sync(new.tenant_id, new.skill_set_code);
  end if;
  return null;
end $$;

drop trigger if exists skill_level_sample_on_card on question_format;
create trigger skill_level_sample_on_card after insert or update of kind, skill_set_code or delete on question_format
  for each row execute function internal.skill_level_sample_from_card();

-- One skill's mistakes made equal to its list. A code no row of `misconception` holds is refused here, since a code
-- with no row joins to nothing and a key alone would let it pass unseen.
create or replace function internal.skill_mistake_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
declare
  missing text;
begin
  select string_agg(c, ', ' order by c) into missing
  from skill_set s cross join unnest(s.misconception_codes) c
  where s.tenant_id = p_tenant and s.code = p_code
    and not exists (select 1 from misconception m where m.tenant_id = p_tenant and m.code = c);
  if missing is not null then
    raise exception 'skill % names mistakes no row of misconception holds: %', p_code, missing
      using errcode = 'foreign_key_violation';
  end if;
  delete from skill_mistake k
  where k.tenant_id = p_tenant and k.skill_code = p_code
    and not exists (select 1 from skill_set s where s.tenant_id = p_tenant and s.code = p_code
                    and k.misconception_code = any(s.misconception_codes));
  insert into skill_mistake (tenant_id, skill_code, misconception_code, op)
  select s.tenant_id, s.code, m.code, m.op
  from skill_set s cross join unnest(s.misconception_codes) c
  join misconception m on m.tenant_id = s.tenant_id and m.code = c
  where s.tenant_id = p_tenant and s.code = p_code
  on conflict (tenant_id, skill_code, misconception_code, op) do nothing;
end $$;

-- One skill's registry links made equal to its rung's list; a code the registry does not hold is refused by its key.
create or replace function internal.skill_registry_link_sync(p_tenant uuid, p_code text) returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from skill_registry_link k
  where k.tenant_id = p_tenant and k.skill_code = p_code
    and not exists (select 1 from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
                    where s.tenant_id = p_tenant and s.code = p_code and k.registry_skill = any(r.skill_codes));
  insert into skill_registry_link (tenant_id, skill_code, registry_skill)
  select s.tenant_id, s.code, c
  from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
  cross join unnest(r.skill_codes) c
  where s.tenant_id = p_tenant and s.code = p_code
  on conflict (tenant_id, skill_code, registry_skill) do nothing;
end $$;

create or replace function internal.skill_links_from_skill_set() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_mistake_sync(new.tenant_id, new.code);
  perform internal.skill_registry_link_sync(new.tenant_id, new.code);
  return null;
end $$;

drop trigger if exists skill_links_on_insert on skill_set;
create trigger skill_links_on_insert after insert on skill_set
  for each row execute function internal.skill_links_from_skill_set();
drop trigger if exists skill_links_on_update on skill_set;
create trigger skill_links_on_update after update on skill_set
  for each row when (row(old.code, old.rung_code, old.misconception_codes)
                     is distinct from row(new.code, new.rung_code, new.misconception_codes))
  execute function internal.skill_links_from_skill_set();

create or replace function internal.skill_registry_link_from_rung() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.skill_registry_link_sync(s.tenant_id, s.code)
  from skill_set s where s.tenant_id = new.tenant_id and s.rung_code = new.code;
  return null;
end $$;

drop trigger if exists skill_registry_link_on_rung on rung;
create trigger skill_registry_link_on_rung after update of skill_codes on rung
  for each row when (old.skill_codes is distinct from new.skill_codes)
  execute function internal.skill_registry_link_from_rung();

-- A mistake written for one more operation is one more row for every skill that names its code.
create or replace function internal.skill_mistake_from_misconception() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into skill_mistake (tenant_id, skill_code, misconception_code, op)
  select s.tenant_id, s.code, new.code, new.op from skill_set s
  where s.tenant_id = new.tenant_id and new.code = any(s.misconception_codes)
  on conflict (tenant_id, skill_code, misconception_code, op) do nothing;
  return null;
end $$;

drop trigger if exists skill_mistake_on_misconception on misconception;
create trigger skill_mistake_on_misconception after insert on misconception
  for each row execute function internal.skill_mistake_from_misconception();

-- Decision B3-2 changes no list: every division mistake a skill names is computed on a division that skill's questions
-- ask (the 8 on Multiplication facts on its Advance fact family). A sample of questions can show that a mistake happens,
-- never that it cannot, so no mistake is removed on a sample's word (ADR 0092).

-- The rows as the lists are today.
do $$
begin
  perform internal.skill_level_sample_sync(s.tenant_id, s.code) from skill_set s;
  perform internal.skill_mistake_sync(s.tenant_id, s.code) from skill_set s;
  perform internal.skill_registry_link_sync(s.tenant_id, s.code) from skill_set s;
end $$;

select internal.apply_conventions();

-- The mirrors are the lists' until their writers move: only the triggers above write them, as their owner. What comes
-- before a skill is a person's to change, so the engine and the site may write it.
do $$
begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    revoke insert, update, delete, truncate on skill_level_sample, skill_mistake, skill_registry_link from app_web, app_engine;
  end if;
end $$;
