-- One approval list for everything new (goals/c5-one-approval-list.yaml, the locked scope of 22 Oct, slice C5): draft
-- beside approved, a second approval before anything reaches a parent; the existing approvals unchanged.
--
-- Approvals lived in three shapes: a skill's level (`skill.level_approved`), a way of asking (`question_type_approval`)
-- and a report for a parent (`parent_note.approved_by`). Each said approved or not; none could say "sent back, and
-- why" (E0 could not store it), and a report reached a parent on one person's word. Now:
--   approval_kind   what is approved, its words, and whether it reaches a parent (rows, vocabulary.json)
--   approval_state  draft, sent back, waiting for a second approval, approved: the list's words (rows)
--   approval        a decision, never edited: approved, or sent back with its reason, by whom and when. A kind's first
--                   approval stays where it always was; this holds what those could not: a sending back, and the
--                   second approval, by someone other than the first, of anything that reaches a parent
--   approval_list   everything new and where it stands, one row each, draft beside approved
-- A report is not sent (`parent_note.sent_at`) until its second approval: the database refuses it.
--
-- Written to run twice.

create table if not exists approval_kind (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenant(id) on delete cascade,
  code            text not null,
  ord             int not null,
  words           text not null,
  reaches_parent  boolean not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists approval_state (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  code        text not null,
  ord         int not null,
  words       text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (tenant_id, code)
);

create table if not exists approval (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenant(id) on delete cascade,
  kind        text not null,
  target      text not null,                 -- what is approved, as the list names it
  decision    text not null check (decision in ('approved', 'sent_back')),
  reason      text check (btrim(reason) <> ''),
  by          text not null check (btrim(by) <> ''),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  check (decision <> 'sent_back' or reason is not null),
  foreign key (tenant_id, kind) references approval_kind (tenant_id, code)
);
create index if not exists approval_target_idx on approval (tenant_id, kind, target, created_at);

drop trigger if exists approval_kept on approval;
create trigger approval_kept before update or delete on approval
  for each statement execute function internal.forbid_change();

create or replace function internal.approval_begins(p_tenant uuid) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into approval_kind (tenant_id, code, ord, words, reaches_parent)
  select p_tenant, v.code, v.ord, v.words, v.reaches_parent
  from (values
    ('skill_level', 0, 'a skill at a level', false),
    ('question_type', 1, 'a way of asking', false),
    ('parent_note', 2, 'a report for a parent', true)
  ) v (code, ord, words, reaches_parent)
  on conflict (tenant_id, code) do nothing;
  insert into approval_state (tenant_id, code, ord, words)
  select p_tenant, v.code, v.ord, v.words
  from (values
    ('draft', 0, 'draft'), ('sent_back', 1, 'sent back'),
    ('waiting_second', 2, 'waiting for a second approval'), ('approved', 3, 'approved')
  ) v (code, ord, words)
  on conflict (tenant_id, code) do nothing;
end $$;

create or replace function internal.approval_begins_on_new_school() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform internal.approval_begins(new.id);
  return new;
end $$;
drop trigger if exists approval_begins on tenant;
create trigger approval_begins after insert on tenant
  for each row execute function internal.approval_begins_on_new_school();

select internal.approval_begins(id) from tenant;

-- Everything new, where it stands: its first approval where it always was, then what `approval` adds.
create or replace view approval_list with (security_invoker = true) as
with firsts as (
  select l.tenant_id, 'skill_level' as kind, l.skill_code || ' ' || l.difficulty as target,
         s.level_approved -> l.difficulty ->> 'by' as first_by,
         (s.level_approved -> l.difficulty ->> 'at')::timestamptz as first_at
  from skill_level l join skill s on s.tenant_id = l.tenant_id and s.code = l.skill_code
  union all
  select q.tenant_id, 'question_type', q.code, a.approved_by, a.approved_at
  from question_type q
  left join lateral (
    select approved_by, approved_at from question_type_approval x
    where x.tenant_id = q.tenant_id and x.question_type = q.code order by approved_at limit 1
  ) a on true
  union all
  select n.tenant_id, 'parent_note', n.id::text, n.approved_by, case when n.approved_by is not null then n.updated_at end
  from parent_note n
), stood as (
  select f.*, k.reaches_parent,
         (select a.reason from approval a
          where a.tenant_id = f.tenant_id and a.kind = f.kind and a.target = f.target and a.decision = 'sent_back'
            and (f.first_at is null or a.created_at > f.first_at)
          order by a.created_at desc, a.id desc limit 1) as sent_back_because,
         (select a.created_at from approval a
          where a.tenant_id = f.tenant_id and a.kind = f.kind and a.target = f.target and a.decision = 'sent_back'
            and (f.first_at is null or a.created_at > f.first_at)
          order by a.created_at desc, a.id desc limit 1) as sent_back_at,
         (select a.by from approval a
          where a.tenant_id = f.tenant_id and a.kind = f.kind and a.target = f.target and a.decision = 'approved'
            and a.by <> f.first_by
          order by a.created_at desc, a.id desc limit 1) as second_by
  from firsts f
  join approval_kind k on k.tenant_id = f.tenant_id and k.code = f.kind
)
select tenant_id, kind, target, first_by, first_at, second_by, sent_back_because,
       case when sent_back_at is not null and (second_by is null) then 'sent_back'
            when first_by is null then 'draft'
            when reaches_parent and second_by is null then 'waiting_second'
            else 'approved' end as state
from stood;

-- A second approval is someone else's, after the first; a sending back needs no first.
create or replace function internal.approval_checked() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  f record;
begin
  if new.decision = 'approved' then
    select first_by, first_at into f from approval_list
    where tenant_id = new.tenant_id and kind = new.kind and target = new.target;
    if f.first_by is null then
      raise exception 'nothing to approve a second time: % % has no first approval', new.kind, new.target
        using errcode = 'check_violation';
    end if;
    if f.first_by = new."by" then
      raise exception 'a second approval is someone else''s: % approved % first', new."by", new.target
        using errcode = 'check_violation';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists approval_checked on approval;
create trigger approval_checked before insert on approval
  for each row execute function internal.approval_checked();

-- Nothing reaches a parent before its second approval.
create or replace function internal.parent_note_sent_when_approved_twice() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.sent_at is not null and old.sent_at is null and not exists (
    select 1 from approval_list
    where tenant_id = new.tenant_id and kind = 'parent_note' and target = new.id::text and state = 'approved'
  ) then
    raise exception 'a report reaches a parent after two approvals, by two people' using errcode = 'check_violation';
  end if;
  return new;
end $$;
drop trigger if exists parent_note_sent_when_approved_twice on parent_note;
create trigger parent_note_sent_when_approved_twice before update of sent_at on parent_note
  for each row execute function internal.parent_note_sent_when_approved_twice();

select internal.apply_conventions();
