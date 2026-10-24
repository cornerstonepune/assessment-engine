import { cache } from "react";
import { sql } from "./db";
import { inScope, type Scope } from "./scope";
import { topics as topicRows } from "./queries-people";
import { classResult, topicFlow, topicStatuses, type Flow, type Sheet, type TopicStatus } from "./topic-flow";
import type { State } from "@/components/status-chip";
import { isoWeek } from "./week";

// What Teaching shows (goals/nav_teacher_scope_and_todo.yaml): every topic of the school in the curriculum's order, with its
// skills, whether each class has been taught it, the topic's flow in each class (lib/topic-flow.ts, derived from the papers on
// record) and how the class stands on it. Read in the classes of the scope.

export type TeachingSkill = { code: string; name: string; approved: boolean; levels: string[] };
export type ClassFlow = { section: string; taught: boolean; flow: Flow };
export type TeachingTopic = {
  code: string;
  name: string;
  subject: string;
  status: TopicStatus;
  /** Classes of the scope that have been taught it / have not. */
  taught: string[];
  untaught: string[];
  skills: TeachingSkill[];
  flows: ClassFlow[];
  result: State;
};

export const teaching = cache(async (scope: Scope): Promise<TeachingTopic[]> => {
  const [topics, skills, sheets, declared, states] = await Promise.all([
    topicRows(scope),
    sql<{ topic: string; code: string; name: string; approved: boolean; levels: string[] }[]>`
      select s.topic_code as topic, s.code, s.name, s.status = 'ratified' as approved,
             coalesce((select array_agg(k order by k) from jsonb_object_keys(s.difficulty) k), '{}') as levels
      from skill s where s.topic_code is not null order by s.ladder_order, s.code`,
    sql<{ topic: string; section: string; kind: string | null; child: string | null; at: string }[]>`
      select s.topic_code as topic, coalesce(si.section, ch.section) as section, si.kind, si.child_id::text as child, si.created_at::text as at
      from sheet_instance si
      join sheet_template st on st.id = si.sheet_template_id
      join skill s on s.tenant_id = st.tenant_id and s.code = st.skill_set_code
      left join child ch on ch.id = si.child_id
      where si.print_status <> 'void' and s.topic_code is not null and ${inScope(scope, sql`coalesce(si.section, ch.section)`)}`,
    sql<{ topic: string }[]>`
      select distinct s.topic_code as topic from week_declaration w
      join skill s on s.code = any(w.skill_sets)
      where w.week = ${isoWeek()} and s.topic_code is not null and ${inScope(scope, sql`w.section`)}`,
    sql<{ topic: string; colour: string; n: number }[]>`
      select s.topic_code as topic, cs.colour, count(*)::int as n
      from child_skill_state k
      join child ch on ch.id = k.child_id and ch.active
      join skill s on s.tenant_id = k.tenant_id and s.code = k.skill_code
      join child_state cs on cs.tenant_id = k.tenant_id and cs.code = k.state and cs.enough
      where s.topic_code is not null and ${inScope(scope, sql`ch.section`)}
      group by 1, 2`,
  ]);
  const status = topicStatuses(
    topics.map((t) => ({ code: t.code, subject: t.subject, taught: t.taught })),
    new Set(declared.map((d) => d.topic)),
  );
  return topics.map((t) => {
    const mine = skills.filter((s) => s.topic === t.code);
    const colour = (c: string) => states.find((x) => x.topic === t.code && x.colour === c)?.n ?? 0;
    return {
      code: t.code,
      name: t.name,
      subject: t.subject,
      status: status.get(t.code) ?? "notTaught",
      taught: t.classes.filter((c) => c.taught).map((c) => c.section),
      untaught: t.classes.filter((c) => !c.taught).map((c) => c.section),
      skills: mine.map(({ code, name, approved, levels }) => ({ code, name, approved, levels })),
      flows: t.classes.map((c) => ({
        section: c.section,
        taught: c.taught,
        flow: topicFlow({
          skills: { total: mine.length, approved: mine.filter((s) => s.approved).length },
          sheets: sheets.filter((x) => x.topic === t.code && x.section === c.section).map((x): Sheet => ({ kind: x.kind, child: x.child, at: x.at })),
          taughtAt: c.taught ? c.at : null,
        }),
      })),
      result: classResult({ red: colour("red"), amber: colour("amber"), green: colour("green") }),
    };
  });
});
