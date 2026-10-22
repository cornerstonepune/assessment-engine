import { sql } from "./db";

// goals/ck1-the-picture-is-the-question.yaml. Nimish, 2026-10-22: the picture shown for question 8 was question 11's.
// A box is shown as the part of the page an answer was read from only when the engine cut it from that question's own
// printed boxes (`boxes`, stored beside it by `boxes.read_page`) and no other question of the same page has the same
// one. Any other box — a region found by words, one given to several questions — is not that question's own, and the
// answer is shown whole instead. Reads `r` (item_result) and `i` (item), as every query of an answer does.
export const ownBox = sql`
  case when coalesce((r.raw_read::jsonb ->> 'boxes')::int, 0) > 0
        and jsonb_typeof(r.raw_read::jsonb -> 'box') = 'array'
        and not exists (
          select 1 from item_result o join item oi on oi.id = o.item_id
           where o.capture_id = r.capture_id and o.id <> r.id and oi.item_key <> i.item_key
             and o.raw_read::jsonb -> 'box' = r.raw_read::jsonb -> 'box'
             and coalesce(o.raw_read::jsonb ->> 'file_page', o.raw_read::jsonb ->> 'page')
                 is not distinct from coalesce(r.raw_read::jsonb ->> 'file_page', r.raw_read::jsonb ->> 'page'))
       then array(select jsonb_array_elements_text(r.raw_read::jsonb -> 'box'))::numeric[] end`;
