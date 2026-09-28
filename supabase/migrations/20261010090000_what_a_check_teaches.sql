-- Every answer a person has checked, with what it teaches the reader (goals/s19-validation-teaches.yaml): the
-- reader's reading, the person's label, how they gave it, the crop the reader read (kept beside the scans,
-- `w3_read/crops.py`), the kind of question and the day the paper was read. One definition, where two had drifted
-- apart in wording: `profiles.checked_rows` (the notebook, `engine read report`, the reader's gold set) and the
-- website's `readerReport` (Marking) both count from here.
--
-- Checked: a person typed its reading (the latest typed one is the label), or signed it off unchanged (the reader's
-- reading is the label). A Right/Wrong/Blank judgement says whether the child is right, not what the child wrote
-- (ADR 0027), so an answer settled by a judgement alone is not here.
create or replace view answer_checked with (security_invoker = true) as
with latest as (
  select distinct on (rc.item_result_id) rc.item_result_id, rc.human_read, rc.judged, rc.by
    from read_correction rc
   order by rc.item_result_id, rc.created_at desc
)
select r.id as item_result_id, r.tenant_id, si.child_id, c.id as capture_id, c.path, c.pages as file_pages,
       c.created_at as read_at, c.created_at::date as read_on,
       i.fmt, i.item_key, coalesce((i.spec ->> 'page')::int, 1) as page, t.batch_id as paper,
       coalesce(r.raw_read::jsonb ->> 'child_answer', '') as reading,
       coalesce(l.human_read, r.raw_read::jsonb ->> 'child_answer', '') as label,
       case when l.item_result_id is not null then 'typed' else 'signed off' end as how,
       l.by,
       coalesce((r.raw_read::jsonb ->> 'confidence')::float, 0) as confidence,
       coalesce(r.raw_read::jsonb ->> 'why', '') as why,
       coalesce(r.raw_read::jsonb ->> 'answer_state', '') as answer_state,
       coalesce(r.raw_read::jsonb ->> 'guess', '') as guess,
       r.raw_read::jsonb -> 'box' as box,
       r.raw_read::jsonb ->> 'crop' as crop,
       -- the reader stood behind its reading: no doubt given, or only ADR 0029's hold ("read as …")
       (coalesce(r.raw_read::jsonb ->> 'why', '') = '' or r.raw_read::jsonb ->> 'why' like 'read as%') as stood,
       regexp_replace(lower(coalesce(r.raw_read::jsonb ->> 'child_answer', '')), '[\s,]', '', 'g')
         = regexp_replace(lower(coalesce(l.human_read, r.raw_read::jsonb ->> 'child_answer', '')), '[\s,]', '', 'g')
         as reader_right
  from item_result r
  join item i on i.id = r.item_id
  join capture c on c.id = r.capture_id
  join sheet_instance si on si.id = c.sheet_instance_id
  join sheet_template t on t.id = si.sheet_template_id
  left join latest l on l.item_result_id = r.id
 where c.superseded_by is null
   and l.judged is null
   and (l.item_result_id is not null or r.state = 'confirmed');

comment on view answer_checked is
  'Every answer a person checked: the reader''s reading, the person''s label (typed, or the reading signed off), the '
  'crop the reader read, the kind of question and the day read. What the notebook, engine read report and Marking count from.';

revoke all on answer_checked from anon, authenticated;
