import { sql } from "./db";

// One count, one meaning (goals/s2b-assessments-declutter.yaml). Nimish, 2026-10-22: the Equal groups assessment said
// "120 waiting" on Assessments while the menu said 75 and Today 103. An answer waiting for a person is counted once, by
// this one fragment, in every place the screens say it: Assessments' list, the assessment's card, Check the answers,
// Today and Marking.
//
// "Waiting" is `answer_standing`'s word (the database's one definition, which `engine read waiting` counts too). This
// adds the one rule a screen needs on top: the answer must be one a person can be shown and act on — on a paper that has
// not been put away, and that belongs to a child. Before this, the list counted an answer on a paper put away while Check
// the answers did not.
//
// A function, not a constant: `sql` is touched only when data is asked for (lib/db.ts), never when the page is imported.
export const awaitingCte = () => sql`
  awaiting as (
    select s.item_result_id, s.sheet_instance_id
    from answer_standing s
    join item_result r on r.id = s.item_result_id
    join item i on i.id = r.item_id
    join sheet_instance si on si.id = s.sheet_instance_id and si.print_status <> 'void'
    where s.standing = 'waiting' and s.child_id is not null
  )`;
