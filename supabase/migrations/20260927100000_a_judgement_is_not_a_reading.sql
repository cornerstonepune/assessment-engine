-- A person who judges an answer Right, Wrong or Blank on the validation queue has said whether the
-- child is right, not what the child wrote. `judgeOne` records who judged as a read_correction whose
-- reading is the engine's own (ADR 0027) — and the reader's gold set read every such row as a
-- verified reading, so a find-the-mistake 75 read as 76 and judged Right scored the reader right on
-- its own misread (2026-09-21). `judged` marks a judgement; `legacy.corrections`, the gold set, reads
-- only rows where it is null.
alter table read_correction add column judged text check (judged in ('correct', 'wrong', 'blank'));

-- The rows the queue wrote before this column: the engine's own reading kept as the person's, on a
-- question whose answer only a person can judge — a written reading of a `text` question that does
-- not agree with its key (an agreement the engine marks by itself), judged right, wrong or blank.
update read_correction rc
   set judged = r.status
  from item_result r
  join item i on i.id = r.item_id
 where r.id = rc.item_result_id
   and rc.human_read = rc.model_read
   and r.status in ('correct', 'wrong', 'blank')
   and i.spec ->> 'kind' = 'text'
   and regexp_replace(rc.model_read, '[^0-9]', '', 'g')
       is distinct from regexp_replace(coalesce(i.responses -> 0 ->> 'answer', ''), '[^0-9]', '', 'g');
