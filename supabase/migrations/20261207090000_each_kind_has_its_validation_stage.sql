-- Validation rules per subject and kind (goals/c4-validation-rules-per-subject-and-kind.yaml, the locked scope of
-- 22 Oct, slice C4): New (every answer to a person), Learning, Trusted, Falls back; every number a row, grown from
-- `kind_trust` (ADR 0060).
--
-- `kind_trust` holds one rule for every kind of question, whatever its subject: its last `marking.agreement_window`
-- checks, trusted at `marking.agreement_gate`. A subject could not have its own, and nothing said a kind had never been
-- checked, or had been trusted and slipped. Now:
--   validation_stage   the four stages, their words and whether every answer goes to a person (rows, vocabulary.json)
--   validation_rule    a subject's numbers, its window and its bar, for all its kinds or for one; each subject starts
--                      with today's two thresholds, so every stage agrees with `kind_trust` as it stands
--   kind_stage         every kind a subject's questions hold, with its checks, the rule it is held to and its stage:
--                        New         no check yet
--                        Learning    checked, never yet trusted
--                        Trusted     its newest window of checks reaches the bar
--                        Falls back  once trusted, below the bar now
-- Marking still reads `kind_trust`; which rule marking follows when a subject's numbers differ is a later slice's.
--
-- Written to run twice.

create table if not exists validation_stage (
  id                      uuid primary key default gen_random_uuid(),
  tenant_id               uuid not null references tenant(id) on delete cascade,
  code                    text not null,
  ord                     int not null,
  words                   text not null,
  every_answer_to_person  boolean not null,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists validation_rule (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenant(id) on delete cascade,
  subject_code  text not null,
  kind          text,                                   -- a question's kind (`item.fmt`); none: every kind of the subject
  window_size   int not null check (window_size > 0),   -- how many of the newest checks are counted
  bar           numeric not null check (bar > 0 and bar <= 1), -- the share of them that must match a person
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  foreign key (tenant_id, subject_code) references subject (tenant_id, code) on update cascade
);
create unique index if not exists validation_rule_one on validation_rule (tenant_id, subject_code, coalesce(kind, ''));

create or replace function internal.validation_begins(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into validation_stage (tenant_id, code, ord, words, every_answer_to_person)
  select p_tenant, v.code, v.ord, v.words, v.to_person
  from (values
    ('new', 0, 'New: every answer to a person', true),
    ('learning', 1, 'Learning', true),
    ('trusted', 2, 'Trusted', false),
    ('falls_back', 3, 'Falls back', true)
  ) v (code, ord, words, to_person)
  on conflict (tenant_id, code) do nothing;
  insert into validation_rule (tenant_id, subject_code, window_size, bar)
  select p_tenant, s.code,
         coalesce((select value::int from threshold where key = 'marking.agreement_window'), 50),
         coalesce((select value from threshold where key = 'marking.agreement_gate'), 0.95)
  from subject s
  where s.tenant_id = p_tenant
  on conflict do nothing;
end $$;

create or replace function internal.validation_begins_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.validation_begins(new.id);
  return new;
end $$;
drop trigger if exists validation_begins on tenant;
create trigger validation_begins after insert on tenant
  for each row execute function internal.validation_begins_on_new_school();

-- A subject added later starts with the same numbers.
create or replace function internal.validation_rule_on_new_subject() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.validation_begins(new.tenant_id);
  return new;
end $$;
drop trigger if exists validation_rule_on_new_subject on subject;
create trigger validation_rule_on_new_subject after insert on subject
  for each row execute function internal.validation_rule_on_new_subject();

select internal.validation_begins(id) from tenant;

create or replace view kind_stage with (security_invoker = true) as
with item_subject as (
  -- a question's subject: its skill's topic's, the skill named or, for a question from an old paper, on its rung
  select i.tenant_id, i.item_key, i.fmt, t.subject_code
  from item i
  join lateral (
    select s.topic_code from skill s
    where s.tenant_id = i.tenant_id and (s.code = i.skill_set_code or (i.skill_set_code is null and s.rung_code = i.rung_code))
    order by (s.code = i.skill_set_code) desc limit 1
  ) s on true
  join topic t on t.tenant_id = i.tenant_id and t.code = s.topic_code
  where i.status = 'active' or exists (select 1 from item_result r where r.item_id = i.id)
), kinds as (
  select distinct tenant_id, subject_code, fmt from item_subject
), ruled as (
  select k.*, r.window_size, r.bar
  from kinds k
  join lateral (
    select window_size, bar from validation_rule r
    where r.tenant_id = k.tenant_id and r.subject_code = k.subject_code and (r.kind = k.fmt or r.kind is null)
    order by r.kind nulls last limit 1
  ) r on true
), checks as (
  -- the checks `kind_trust` reads, oldest first, numbered within their subject and kind
  select q.tenant_id, q.subject_code, a.fmt, a.reader_right,
         row_number() over (partition by q.tenant_id, q.subject_code, a.fmt
                            order by a.read_at, a.item_key, a.item_result_id) as i
  from answer_checked a
  join item_subject q on q.tenant_id = a.tenant_id and q.item_key = a.item_key
  where a.stood
), windows as (
  -- at each check, its window: it and the checks before it, as many as the rule counts
  select c.tenant_id, c.subject_code, c.fmt, c.i, r.window_size, r.bar,
         count(*)::int as n, count(*) filter (where w.reader_right)::int as n_right
  from checks c
  join ruled r using (tenant_id, subject_code, fmt)
  join checks w on w.tenant_id = c.tenant_id and w.subject_code = c.subject_code and w.fmt = c.fmt
               and w.i > c.i - r.window_size and w.i <= c.i
  group by 1, 2, 3, 4, 5, 6
), standing as (
  select tenant_id, subject_code, fmt,
         max(i)::int as checks,
         bool_or(n >= window_size and n_right >= bar * window_size) as ever_trusted,
         (array_agg(n order by i desc))[1] as n,
         (array_agg(n_right order by i desc))[1] as n_right,
         (array_agg(n >= window_size and n_right >= bar * window_size order by i desc))[1] as trusted
  from windows
  group by 1, 2, 3
)
select r.tenant_id, r.subject_code, r.fmt as kind, r.window_size, r.bar,
       coalesce(s.checks, 0) as checks, coalesce(s.n, 0) as n, coalesce(s.n_right, 0) as "right",
       coalesce(s.trusted, false) as trusted,
       case when s.checks is null then 'new'
            when s.trusted then 'trusted'
            when s.ever_trusted then 'falls_back'
            else 'learning' end as stage
from ruled r
left join standing s using (tenant_id, subject_code, fmt);

select internal.apply_conventions();
