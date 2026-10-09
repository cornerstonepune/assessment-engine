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
