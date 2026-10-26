// The Assessments page read by topic (goals/asm2_by_topic_and_checking.yaml). Nimish, 26 Oct 2026: "There must be some view
// where I'll be able to just see the assessments by topic also. Let's say if someone wants to go and see addition, they can
// see all the assessments under addition." One small query counts every topic's assessments; only the topic that is open
// has its rows read, one page of them (`assessmentList` with a page).
import { sql } from "./db";
import { actionOfSig } from "./assessment-steps";
import {
  narrowed,
  NO_TOPIC,
  papersCte,
  sigSql,
  type PaperFilter,
} from "./queries-papers";
import { EVERY_CLASS, type Scope } from "./scope";

/** What waits on the educator herself: an approval, answers to check, papers to sign off. */
const NEEDS_YOU = new Set(["approve", "check", "signoff"]);

export type TopicGroup = {
  /** The topic's code, or `NO_TOPIC` for assessments whose questions are on none. */
  code: string;
  name: string;
  /** The code of its subject. */
  subject: string | null;
  /** Its assessments, and of them those whose next step is the educator's. */
  total: number;
  needYou: number;
};

/** Every topic with at least one assessment among the filter's, the ones with something for the educator first, then in the
 *  curriculum's own order. An assessment on two topics is counted under each. */
export async function topicGroups(
  f: PaperFilter,
  scope: Scope = EVERY_CLASS,
): Promise<TopicGroup[]> {
  const [counts, topics] = await Promise.all([
    sql<{ topic: string | null; sig: string; n: number }[]>`
      with ${papersCte()},
      g as (
        select ${sigSql()} as sig, jsonb_agg(topics) as topics
        from papers where ${narrowed({ ...f, topic: undefined }, scope)}
        group by kind, section, week, set_key
      ),
      x as (
        select sig, (select coalesce(array_agg(distinct v), '{}'::text[]) from jsonb_array_elements(topics) e, jsonb_array_elements_text(e) v) as listed
        from g
      )
      select t as topic, sig, count(*)::int as n
      from x cross join lateral unnest(case when cardinality(listed) = 0 then array[null::text] else listed end) t
      group by 1, 2`,
    sql<
      { code: string; name: string; subject: string | null; ord: number }[]
    >`select code, name, subject_code as subject, ord from topic order by ord`,
  ]);
  const by = new Map<string, { total: number; needYou: number }>();
  for (const c of counts) {
    const key = c.topic ?? NO_TOPIC;
    const at = by.get(key) ?? { total: 0, needYou: 0 };
    at.total += c.n;
    if (NEEDS_YOU.has(actionOfSig(c.sig))) at.needYou += c.n;
    by.set(key, at);
  }
  const named = topics
    .filter((t) => by.has(t.code))
    .map((t) => ({
      code: t.code,
      name: t.name,
      subject: t.subject,
      ...by.get(t.code)!,
    }));
  const none = by.get(NO_TOPIC);
  return [
    ...named,
    ...(none
      ? [{ code: NO_TOPIC, name: "No topic yet", subject: null, ...none }]
      : []),
  ].sort((a, b) => Number(b.needYou > 0) - Number(a.needYou > 0));
}

/** The topics' names, to say a code in the school's words. */
export const topicNamesOf = () =>
  sql<{ code: string; name: string }[]>`select code, name from topic`;
