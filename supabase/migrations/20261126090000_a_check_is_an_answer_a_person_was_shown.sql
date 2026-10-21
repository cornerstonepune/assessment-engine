-- A check is an answer a person was shown (ADR 0032, docs/notes/reader-learns-audit.md). Until now an answer signed off
-- with its paper counted as "the reader was right" whether or not anyone had been asked about it: an answer the reader
-- settled alone (no reason to wait, `raw_read.why` empty) was confirmed with the paper, or with every paper of a child
-- at once on Growth, and then counted as a check the reader passed. It can only ever say "right", so it raised the
-- reader's score with no person's word behind it. On live, 21 Oct: 85 such answers among the checks, 8 of them in one
-- kind's trust window. Once a kind is trusted, every right answer of it settled alone would have joined its window
-- as another right check, keeping the trust by its own word; the spot check (`marking.spot_check_rate`) is the check
-- that keeps it honest, and only what a person was shown can be.
--
-- Signed off now counts only where the answer waited for a person: its reading carries the reason it waited (a doubt
-- of the reader's, or marking's hold: "read as a right answer; a person checks…", "spot-checked", "read as a wrong
-- answer…"). A typed answer counts as before. `in_boxes`: the reading was made in the boxes of a paper this system
-- printed (`boxes.read_page`, the digit reader of ADR 0035) rather than found in a region, so a child's confidence
-- floor is measured on the reader that will read the next paper (`profiles.build`).
create or replace view answer_checked with (security_invoker = true) as
with latest as (
  select distinct on (rc.item_result_id) rc.item_result_id, rc.human_read, rc.judged, rc.by
    from read_correction rc
   order by rc.item_result_id, rc.created_at desc
)
select r.id as item_result_id, r.tenant_id, si.child_id, c.id as capture_id, c.path, c.pages as file_pages,
       c.created_at as read_at, c.created_at::date as read_on,
       i.fmt, i.item_key, coalesce((r.raw_read::jsonb ->> 'page')::int, (i.spec ->> 'page')::int, 1) as page, t.batch_id as paper,
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
         as reader_right,
       coalesce((r.raw_read::jsonb ->> 'file_page')::int, (r.raw_read::jsonb ->> 'page')::int, (i.spec ->> 'page')::int, 1)
         as file_page,
       coalesce(r.raw_read::jsonb ->> 'why', '') like '%not a number%' as never_read,
       r.raw_read::jsonb ? 'boxes' as in_boxes
  from item_result r
  join item i on i.id = r.item_id
  join capture c on c.id = r.capture_id
  join sheet_instance si on si.id = c.sheet_instance_id
  join sheet_template t on t.id = si.sheet_template_id
  left join latest l on l.item_result_id = r.id
 where c.superseded_by is null
   and l.judged is null
   and (l.item_result_id is not null
        or (r.state = 'confirmed' and coalesce(r.raw_read::jsonb ->> 'why', '') <> ''));

comment on view answer_checked is
  'Every answer a person checked: typed, or signed off after it waited for a person (its reading carries why). The '
  'reader''s reading, the person''s label, the crop, the kind, the day read, and whether it was read in boxes. What the '
  'notebook, kind_trust, engine read report and Marking count from (ADR 0032).';
