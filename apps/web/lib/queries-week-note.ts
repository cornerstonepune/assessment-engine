import { sql } from "./db";
import { awaitingCte } from "./queries-counts";
import { many } from "./needs-you";
import { inScope, type Scope } from "./scope";

// Today's five lines: what the system now knows this week (goals/s1-subject-class-and-today.yaml), for the classes and
// the subject chosen at the top. Every number is counted here, by code, from the rows the pages read: the papers read
// (capture, item_result), what a person checked (read_correction), where each child stands (child_skill_state, as the
// Children page colours it) and the mistakes named (evidence_event). A skill's subject is its topic's (skill_set →
// topic → subject). The week is the ISO week, from Monday.

export type WeekNote = {
  papers: number;
  answers: number;
  checked: number;
  waiting: number;
  children: number;
  secure: number;
  practising: number;
  help: number;
  mistake: { name: string; children: number; times: number } | null;
  helpTwice: number;
};

/** A skill set's rung is in the subject: the rung's skill set's topic is the subject's. */
const rungIn = (subject: string, rung: ReturnType<typeof sql>) => sql`exists (
  select 1 from skill_set ss join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
  where ss.rung_code = ${rung} and t.subject_code = ${subject})`;

export async function weekNote(scope: Scope, subject: string): Promise<WeekNote> {
  const [[read], [stand], [mistake]] = await Promise.all([
    sql<{ papers: number; answers: number; checked: number; waiting: number }[]>`
      with ${awaitingCte()},
      answers as (
        select k.id as capture, r.id, r.status
        from capture k
        join sheet_instance si on si.id = k.sheet_instance_id
        left join child ch on ch.id = si.child_id
        join item_result r on r.capture_id = k.id
        join item i on i.id = r.item_id
        join skill_set ss on ss.tenant_id = i.tenant_id and ss.code = i.skill_set_code
        join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code
        where k.superseded_by is null and k.created_at >= date_trunc('week', now()) and t.subject_code = ${subject}
          and ${inScope(scope, sql`coalesce(si.section, ch.section)`)}
      )
      select count(distinct capture)::int as papers, count(*)::int as answers,
             (select count(distinct c.item_result_id)::int from read_correction c where c.item_result_id in (select id from answers)) as checked,
             count(*) filter (where id in (select item_result_id from awaiting))::int as waiting
      from answers`,
    sql<{ children: number; secure: number; practising: number; help: number; help_twice: number }[]>`
      with kids as (select id from child where active and ${inScope(scope, sql`section`)}),
      states as (
        select s.child_id, s.rung_code, cs.colour
        from child_skill_state s join child_state cs on cs.tenant_id = s.tenant_id and cs.code = s.state
        where s.child_id in (select id from kids) and cs.enough and ${rungIn(subject, sql`s.rung_code`)}
      )
      select (select count(*)::int from kids) as children,
             count(distinct child_id) filter (where colour = 'green')::int as secure,
             count(distinct child_id) filter (where colour = 'amber')::int as practising,
             count(distinct child_id) filter (where colour = 'red')::int as help,
             (select count(*)::int from (select child_id from states where colour = 'red' group by child_id
                                         having count(distinct rung_code) >= 2) x) as help_twice
      from states`,
    sql<{ name: string; children: number; times: number }[]>`
      select (select min(m.name) from misconception m where m.tenant_id = e.tenant_id and m.code = c.code) as name,
             count(distinct e.child_id)::int as children, count(*)::int as times
      from evidence_event e cross join lateral unnest(e.misconception_codes) c(code)
      join child ch on ch.id = e.child_id
      where e.confirmed_by is not null and e.observed_at >= date_trunc('week', now()) and ch.active
        and ${inScope(scope, sql`ch.section`)} and ${rungIn(subject, sql`e.rung_code`)}
      group by e.tenant_id, c.code order by count(distinct e.child_id) desc, count(*) desc, c.code limit 1`,
  ]);
  return {
    ...read,
    children: stand.children,
    secure: stand.secure,
    practising: stand.practising,
    help: stand.help,
    helpTwice: stand.help_twice,
    mistake: mistake ?? null,
  };
}

const is = (n: number) => (n === 1 ? "is" : "are");

/** The five lines, said as an educator says them. */
export function noteLines(w: WeekNote): string[] {
  return [
    w.papers
      ? `${many(w.papers, "paper")} came back this week, and ${many(w.answers, "answer")} ${w.answers === 1 ? "was" : "were"} read.`
      : "No paper has come back this week yet.",
    `${w.checked ? `A person checked ${many(w.checked, "answer")}` : "No answer has been checked by a person yet"}; ${
      w.waiting ? `${many(w.waiting, "answer")} from this week ${w.waiting === 1 ? "waits" : "wait"} for a person.` : "none of this week's waits for a person."
    }`,
    `${w.secure} of ${many(w.children, "child", "children")} ${is(w.secure)} secure on a skill; ${w.help} ${w.help === 1 ? "needs" : "need"} help on one, and ${w.practising} ${is(w.practising)} practising one.`,
    w.mistake
      ? `The mistake seen most this week: ${w.mistake.name}, by ${many(w.mistake.children, "child", "children")}, ${many(w.mistake.times, "time")}.`
      : "No named mistake was seen this week.",
    `${many(w.helpTwice, "child", "children")} ${w.helpTwice === 1 ? "needs" : "need"} help on two or more skills.`,
  ];
}
