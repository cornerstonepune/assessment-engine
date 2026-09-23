-- U3, Marking (goals/u3-marking.yaml): every answer on a read paper stands in exactly one place — still waiting
-- for a person, settled by the engine, or checked by a person — and the Marking screen and `engine read waiting`
-- count it from this one definition, so the two cannot disagree.
--
-- "Checked by a person" is a `read_correction` row: a person typed what the child wrote, confirmed the reader's
-- reading, or judged Right / Wrong / Blank. The queue already left that row when it judged; a paper's or a child's
-- own Right / Wrong / Blank (resolve_result) did not, so a person's judgement there was indistinguishable from the
-- engine's mark. It now leaves the same row. Judgements made through resolve_result before this migration left no
-- such row and are counted as the engine's; nothing records who made them, so nothing here guesses.

create or replace function resolve_result(p_result_id uuid, p_status text, p_codes text[], p_by text)
returns void language plpgsql security definer set search_path = public as $$
declare child uuid; cap uuid;
begin
  if p_status not in ('correct', 'wrong', 'blank') then
    raise exception 'resolve_result: status must be correct, wrong or blank, not %', p_status;
  end if;
  select si.child_id, c.id into child, cap from item_result r
    join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id
   where r.id = p_result_id and r.state = 'candidate';
  if child is null then raise exception 'resolve_result: no candidate result %', p_result_id; end if;
  -- who judged it, with the engine's reading unchanged (rule 4): the same row the queue's judgement leaves
  insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by, judged)
  select r.tenant_id, child, cap, r.id, coalesce(r.raw_read::jsonb ->> 'child_answer', ''),
         coalesce(r.raw_read::jsonb ->> 'child_answer', ''), p_by, p_status
    from item_result r where r.id = p_result_id;
  update item_result set status = p_status, misconception_codes = coalesce(p_codes, '{}')
   where id = p_result_id and state = 'candidate';
  perform confirm_results(child, p_by, cap);
end $$;

create or replace view answer_standing with (security_invoker = true) as
select r.id as item_result_id, r.tenant_id, c.sheet_instance_id, si.child_id,
       case when r.status in ('unreadable', 'needs_teacher') then 'waiting'
            when exists (select 1 from read_correction rc where rc.item_result_id = r.id) then 'person'
            else 'engine' end as standing,
       r.state = 'confirmed' as signed_off
from item_result r
join capture c on c.id = r.capture_id
join sheet_instance si on si.id = c.sheet_instance_id
where c.superseded_by is null;

comment on view answer_standing is
  'Each answer on a live read: waiting (for a person), engine (settled by the engine), person (checked by a person); '
  'and whether a person has signed it off. The one definition Marking and `engine read waiting` count from.';

revoke all on answer_standing from anon, authenticated;
