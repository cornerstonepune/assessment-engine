-- Every answer a question asks for is marked and shown against its own key (goals/md0a-every-answer-counts.yaml).
-- A printed question can ask for more than one answer — an estimate and the exact answer, a check and whether the sum
-- was right — and each answer is its own result (`item_result.rid`). Wherever a result was marked or shown, its
-- question's first answer stood in for its own, so an exact answer was marked and shown against the estimate's key.
-- This is the one rule the engine's queries and the website's read: a result is for the response its `rid` names.
-- A result naming none falls back to its question's first answer, as everything did before, and `engine audit`
-- names it ("every answer names a response of its question").
create or replace function public.result_response(p_responses jsonb, p_rid text)
returns jsonb
language sql immutable as $$
  select coalesce((select x from jsonb_array_elements(p_responses) x where x ->> 'rid' = p_rid limit 1),
                  p_responses -> 0)
$$;

grant execute on function public.result_response(jsonb, text) to app_web, app_engine;

-- Which of its question's answers a result is, so a person shown two cards for one question knows which one they
-- judge: "answer 2 of 2 · exact". Null where the question asks for one answer, so nothing changes on those cards.
create or replace function public.result_part(p_responses jsonb, p_rid text)
returns text
language sql immutable as $$
  select 'answer ' || o || ' of ' || jsonb_array_length(p_responses) || coalesce(' · ' || nullif(x ->> 'label', ''), '')
    from jsonb_array_elements(p_responses) with ordinality e(x, o)
   where x ->> 'rid' = p_rid and jsonb_array_length(p_responses) > 1
   limit 1
$$;

grant execute on function public.result_part(jsonb, text) to app_web, app_engine;

-- The question number a result is shown under. An old paper's is in its key ("legacy/G3-QUIZ20/4a" → 4a). A library
-- worksheet's is numbered per copy, so the reader records it on the result (`raw_read.slot`: "3", or "3.ans" for the
-- question's second answer → 3). A library result read before it was recorded has none, and shows none, as before.
create or replace function public.result_slot(p_item_key text, p_raw jsonb)
returns text
language sql immutable as $$
  select coalesce(nullif(split_part(p_item_key, '/', 3), ''), split_part(p_raw ->> 'slot', '.', 1), '')
$$;

-- Where a result sits among its question's answers, 1 for the first, so two answers to one question show in the order
-- they print.
create or replace function public.result_order(p_responses jsonb, p_rid text)
returns int
language sql immutable as $$
  select o::int from jsonb_array_elements(p_responses) with ordinality e(x, o) where x ->> 'rid' = p_rid limit 1
$$;

grant execute on function public.result_slot(text, jsonb) to app_web, app_engine;
grant execute on function public.result_order(jsonb, text) to app_web, app_engine;

-- A checked answer's page, and the page of its copy's file the photograph is (`file_page`): a library worksheet's
-- question has no page in the bank's row, so the reader records both on the result, as the website already reads them.
-- Read from the bank's row alone, every library answer was on page 1, and the second reader, now reaching a library
-- copy's answers, cropped page 1 at a page-2 answer's place. `never_read`: an answer the reader was never handed, its
-- reason saying it is "not a number" (`boxes.FOR_A_PERSON`, an old paper's sign question) — a person reads it, so it
-- is no measure of the reader on the website, as in `engine read report` (`profiles.never_read`).
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
       coalesce(r.raw_read::jsonb ->> 'why', '') like '%not a number%' as never_read
  from item_result r
  join item i on i.id = r.item_id
  join capture c on c.id = r.capture_id
  join sheet_instance si on si.id = c.sheet_instance_id
  join sheet_template t on t.id = si.sheet_template_id
  left join latest l on l.item_result_id = r.id
 where c.superseded_by is null
   and l.judged is null
   and (l.item_result_id is not null or r.state = 'confirmed');
