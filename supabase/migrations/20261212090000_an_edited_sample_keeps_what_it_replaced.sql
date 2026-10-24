-- An educator changes an English sample, or the kinds a level asks, and nothing earlier is lost
-- (goals/edt_edit_samples_and_kinds.yaml). Nimish, 2026-10-24: "What happens if he wants to make any changes there? …
-- It should simply have the capability to edit the skill, where the nature or the description of the skill can be
-- changed."
--
-- `english_sample` is the seed's (PR #321): `engine load` upserts it on every deploy, so an edit written there would be
-- overwritten by the next one. An edit is its own row instead, and is never changed:
--   english_sample_edit      one saved version of one sample (skill, level, kind, number): the whole sample as saved,
--                            the sample it replaced, who and when; a removal is a version too. The newest wins.
--   skill_level_kind_change  a kind added to or taken from a level, who and when; the newest says where it stands, and
--                            a load does not bring back a kind a person took away
--   english_sample_now       the samples as they stand: the newest edit where there is one, else the seed's
-- Additive only: no existing table, column or row is changed. The engine writes both ledgers, after its checks
-- (engine/w1_bank/english_check.py); the website reads them.
--
-- Written to run twice.

create table if not exists english_sample_edit (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  skill_code     text not null,
  difficulty     text not null,
  question_type  text not null,
  ord            smallint not null check (ord >= 1),
  removed        boolean not null default false,
  -- {ask, passage_code, text, options, answer, accept, rubric_code, key_points, not_words, wrong: [{answer,
  -- mistake_code}]}, as english_sample and english_sample_wrong hold them; none when the sample is removed
  sample         jsonb check (removed or sample is not null),
  replaced       jsonb,                         -- the sample as it stood before, in the same shape; none for a new one
  edited_by      text not null check (btrim(edited_by) <> ''),
  created_at     timestamptz not null default clock_timestamp(),  -- two saves in one sitting are still in order
  updated_at     timestamptz not null default now()
);
create index if not exists english_sample_edit_slot_idx
  on english_sample_edit (tenant_id, skill_code, difficulty, question_type, ord, created_at);

drop trigger if exists english_sample_edit_kept on english_sample_edit;
create trigger english_sample_edit_kept before update or delete on english_sample_edit
  for each statement execute function internal.forbid_change();

create table if not exists skill_level_kind_change (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenant(id) on delete cascade,
  skill_code     text not null,
  difficulty     text not null,
  question_type  text not null,
  added          boolean not null,
  changed_by     text not null check (btrim(changed_by) <> ''),
  created_at     timestamptz not null default clock_timestamp(),
  updated_at     timestamptz not null default now()
);
create index if not exists skill_level_kind_change_idx
  on skill_level_kind_change (tenant_id, skill_code, difficulty, question_type, created_at);

drop trigger if exists skill_level_kind_change_kept on skill_level_kind_change;
create trigger skill_level_kind_change_kept before update or delete on skill_level_kind_change
  for each statement execute function internal.forbid_change();

create or replace view english_sample_now with (security_invoker = true) as
with last as (
  select distinct on (x.tenant_id, x.skill_code, x.difficulty, x.question_type, x.ord) x.*
  from english_sample_edit x
  order by x.tenant_id, x.skill_code, x.difficulty, x.question_type, x.ord, x.created_at desc, x.id desc
)
select e.tenant_id, e.skill_code, e.difficulty, e.question_type, e.ord, e.ask, e.passage_code, e.text, e.options,
       e.answer, e.accept, e.rubric_code, e.key_points, e.not_words,
       coalesce((select jsonb_agg(jsonb_build_object('answer', w.answer, 'mistake_code', w.mistake_code)
                                  order by w.answer)
                 from english_sample_wrong w where w.sample_id = e.id), '[]'::jsonb) as wrong,
       null::text as edited_by, null::timestamptz as edited_at, 0::bigint as earlier
from english_sample e
where not exists (select 1 from last l where l.tenant_id = e.tenant_id and l.skill_code = e.skill_code
                    and l.difficulty = e.difficulty and l.question_type = e.question_type and l.ord = e.ord)
union all
select l.tenant_id, l.skill_code, l.difficulty, l.question_type, l.ord, l.sample ->> 'ask', l.sample ->> 'passage_code',
       l.sample ->> 'text', nullif(l.sample -> 'options', 'null'::jsonb), l.sample -> 'answer',
       coalesce(nullif(l.sample -> 'accept', 'null'::jsonb), '[]'::jsonb), l.sample ->> 'rubric_code',
       nullif(l.sample -> 'key_points', 'null'::jsonb), nullif(l.sample -> 'not_words', 'null'::jsonb),
       coalesce(nullif(l.sample -> 'wrong', 'null'::jsonb), '[]'::jsonb), l.edited_by, l.created_at,
       (select count(*) from english_sample_edit p where p.tenant_id = l.tenant_id and p.skill_code = l.skill_code
          and p.difficulty = l.difficulty and p.question_type = l.question_type and p.ord = l.ord and p.id <> l.id)
from last l
where not l.removed;

-- The engine writes; the website reads.
do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant select, insert on english_sample_edit, skill_level_kind_change to app_engine;
    grant select on english_sample_now to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant select on english_sample_edit, skill_level_kind_change, english_sample_now to app_web;
  end if;
end $$;

select internal.apply_conventions();
