-- Who sees a child's answers and papers (goals/own_who_sees_answers.yaml). Nimish, 27 Oct 2026: "The skill and the
-- curriculum is something at a subject level that is open to all teachers ... but their assessments, answers to be
-- checked etc. should be restricted to their grade. Right now 147 answers to check comes to everyone. But Achal should
-- only see the papers he has uploaded."
--
-- The rule lives here, in `staff_sees`, and nowhere else: the website passes the signed-in person in and asks it of
-- every answer, paper, count and child it shows or acts on (apps/web/lib/reach.ts). To change who sees what, replace
-- that one function in a new migration.

-- 1. Each member of staff has an id: the staff list is a config row (`app.staff`), so each entry gets one, filled in
--    whichever door adds a person (the website, `engine staff add`), and kept when the entry is rewritten.
create or replace function internal.staff_have_ids() returns trigger language plpgsql as $$
begin
  if new.key = 'app.staff' and jsonb_typeof(new.value) = 'array' then
    new.value := (
      select coalesce(jsonb_agg(case when s ? 'id' then s else s || jsonb_build_object('id', gen_random_uuid()) end
                                order by n), '[]'::jsonb)
      from jsonb_array_elements(new.value) with ordinality as e(s, n));
  end if;
  return new;
end $$;

drop trigger if exists staff_have_ids on config;
create trigger staff_have_ids before insert or update on config
  for each row when (new.key = 'app.staff') execute function internal.staff_have_ids();

update config set value = value where key = 'app.staff';

-- The staff id an email signs in as; null for an email on no one's entry (never a guess).
create or replace function public.staff_id(p_email text) returns uuid language sql stable as $$
  select (s ->> 'id')::uuid from config c, jsonb_array_elements(c.value) s
  where c.key = 'app.staff' and lower(s ->> 'email') = lower(trim(p_email)) limit 1
$$;

-- 2. Who put a scan in: on the file's run and on every paper read from it. A row from before today has none, and only
--    the class rule applies to it.
alter table flow_run add column if not exists uploaded_by uuid;
alter table capture add column if not exists uploaded_by uuid;
create index if not exists capture_uploaded_by_idx on capture (uploaded_by) where uploaded_by is not null;

-- 3. A worksheet's subject: that of its questions' topics (one of them, by code, where a paper spans two).
create or replace function public.sheet_subject(p_template uuid) returns text language sql stable as $$
  select min(tp.subject_code)
  from sheet_template t
  join skill s on s.tenant_id = t.tenant_id
    and (s.code = t.skill_set_code or s.code in (select i.skill_set_code from item i where i.id = any(t.item_ids)))
  join topic tp on tp.tenant_id = s.tenant_id and tp.code = s.topic_code
  where t.id = p_template
$$;

-- 4. THE RULE. A coordinator sees everything. An educator sees a thing they put in themselves; otherwise a thing of a
--    class on their staff entry, in a subject on it (no subject named there, or none known for the thing, is every
--    subject). A child and a class have no subject and no uploader: the class alone decides. Asked with no class at all,
--    it says whether the person sees every class.
create or replace function public.staff_sees(
  p_role text, p_classes text[], p_subjects text[], p_staff uuid,
  p_section text, p_subject text, p_uploaded_by uuid
) returns boolean language sql immutable as $$
  select coalesce(
    p_role = 'coordinator'
    or (p_uploaded_by is not null and p_uploaded_by = p_staff)
    or (p_section = any(p_classes)
        and (cardinality(coalesce(p_subjects, '{}')) = 0 or p_subject is null or p_subject = any(p_subjects))),
    false)
$$;

-- The rule asked of one printed copy: its class (its own, or its child's), its subject, and whether this person put in
-- any reading of it still standing. Cheapest question first, each still the rule's: of no class at all (a person who
-- sees every class is answered without reading the copy), then of its uploaders, then of its class alone; its subject,
-- which only ever narrows, is read only for a copy whose class already passes.
create or replace function public.staff_sees_sheet(
  p_role text, p_classes text[], p_subjects text[], p_staff uuid, p_sheet uuid
) returns boolean language sql stable as $$
  select staff_sees(p_role, p_classes, p_subjects, p_staff, null, null, null)
    or exists (select 1 from capture c
               where c.sheet_instance_id = p_sheet and c.superseded_by is null
                 and staff_sees(p_role, p_classes, p_subjects, p_staff, null, null, c.uploaded_by))
    or coalesce((
      select case when staff_sees(p_role, p_classes, p_subjects, p_staff, coalesce(si.section, ch.section), null, null)
                  then staff_sees(p_role, p_classes, p_subjects, p_staff, coalesce(si.section, ch.section),
                                  sheet_subject(si.sheet_template_id), null)
                  else false end
      from sheet_instance si left join child ch on ch.id = si.child_id
      where si.id = p_sheet), false)
$$;

-- The rule asked of one scan: the copy it was read as, or, for a scan not yet sorted onto any copy, its uploader alone.
create or replace function public.staff_sees_capture(
  p_role text, p_classes text[], p_subjects text[], p_staff uuid, p_capture uuid
) returns boolean language sql stable as $$
  select coalesce((
    select staff_sees(p_role, p_classes, p_subjects, p_staff, null, null, c.uploaded_by)
           or (c.sheet_instance_id is not null and staff_sees_sheet(p_role, p_classes, p_subjects, p_staff, c.sheet_instance_id))
    from capture c where c.id = p_capture), false)
$$;

do $$ begin
  if exists (select from pg_roles where rolname = 'app_engine') then
    grant execute on function public.staff_id(text), public.sheet_subject(uuid),
      public.staff_sees(text, text[], text[], uuid, text, text, uuid),
      public.staff_sees_sheet(text, text[], text[], uuid, uuid),
      public.staff_sees_capture(text, text[], text[], uuid, uuid) to app_engine;
  end if;
  if exists (select from pg_roles where rolname = 'app_web') then
    grant execute on function public.sheet_subject(uuid),
      public.staff_sees(text, text[], text[], uuid, text, text, uuid),
      public.staff_sees_sheet(text, text[], text[], uuid, uuid),
      public.staff_sees_capture(text, text[], text[], uuid, uuid) to app_web;
  end if;
end $$;

select internal.apply_conventions();
