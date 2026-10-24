import { cache } from "react";
import { sql } from "./db";
import type { Session } from "./auth";
import { decidable } from "./decides";
import { grades } from "./queries";
import { asksWaiting, topics } from "./queries-people";
import { homeByClass } from "./queries-make";
import { checkQueue } from "./queries-read";
import { classPacksWaiting, reportsWaiting } from "./queries-today";
import { inScope, scopeOf } from "./scope";
import { buildTasks, type Sources, type Task } from "./todo";
import { isoWeek, weekWords } from "./week";
import { mayUse } from "./access";
import { choices } from "./choices";

type PaperRef = { id: string; section: string | null; code: string; topic: string | null; topic_name: string | null; subject: string | null };

/** The subject and topic of a paper: those of the skill set its worksheet is of (none for a paper made of several). */
const paperRefs = (ids: string[]) =>
  ids.length
    ? sql<PaperRef[]>`
        select si.id::text, coalesce(si.section, ch.section) as section, si.qr_code as code,
               t.code as topic, t.name as topic_name, t.subject_code as subject
        from sheet_instance si
        join sheet_template st on st.id = si.sheet_template_id
        left join child ch on ch.id = si.child_id
        left join skill s on s.tenant_id = st.tenant_id and s.code = st.skill_set_code
        left join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
        where si.id = any(${ids}::uuid[])`
    : Promise.resolve([] as PaperRef[]);

/** Every task waiting on this person, each with its own item to open: in the classes they see (a skill is the school's: it is
 *  seen in the subjects they teach, of every grade), and only the decisions that are theirs (lib/decides.ts). Once per request, whoever asks (the menu's count, the page). */
export const tasksFor = cache(async (me: Session): Promise<Task[]> => {
  const scope = scopeOf(me);
  const [g, may, offered] = await Promise.all([grades(), decidable(me), choices()]);
  const [skills, home, queue, signoff, packs, reports, tps, generate, asks, empty] = await Promise.all([
    may("skills")
      ? sql<{ code: string; name: string; grade: string; topic: string | null; topic_name: string | null; subject: string | null; levels: number }[]>`
          select s.code, s.name, s.grade, t.code as topic, t.name as topic_name, t.subject_code as subject,
                 (select count(*)::int from jsonb_object_keys(s.difficulty)) as levels
          from skill s left join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
          where s.status <> 'ratified'
          order by t.ord, s.ladder_order, s.code`
      : Promise.resolve([]),
    may("home_papers") ? homeByClass(isoWeek(), scope) : Promise.resolve([]),
    may("answers") ? checkQueue(scope) : Promise.resolve([]),
    may("papers")
      ? sql<{ id: string; n: number }[]>`
          select si.id::text, count(*) filter (where r.state = 'candidate')::int as n
          from sheet_instance si left join child ch on ch.id = si.child_id
          join capture c on c.sheet_instance_id = si.id and c.superseded_by is null
          join item_result r on r.capture_id = c.id
          where ${inScope(scope, sql`coalesce(si.section, ch.section)`)}
          group by si.id having count(*) filter (where r.state = 'candidate') > 0`
      : Promise.resolve([]),
    may("class_papers") ? classPacksWaiting(scope) : Promise.resolve([]),
    may("reports") ? reportsWaiting(scope) : Promise.resolve([]),
    topics(scope),
    sql<{ topic: string; topic_name: string; subject: string; section: string }[]>`
      select t.code as topic, t.name as topic_name, t.subject_code as subject, k.section
      from topic t
      cross join (select distinct section from child where active and ${inScope(scope, sql`section`)}) k
      where taught_in(t.tenant_id, t.code, k.section)
        and not exists (
          select 1 from sheet_instance si
          join sheet_template st on st.id = si.sheet_template_id
          join skill s on s.tenant_id = st.tenant_id and s.code = st.skill_set_code
          where s.topic_code = t.code and si.kind = 'assessment' and si.print_status <> 'void'
            and coalesce(si.section, (select ch.section from child ch where ch.id = si.child_id)) = k.section)
      order by t.ord, k.section`,
    asksWaiting(),
    sql<{ n: number }[]>`
      select count(*)::int as n from sheet_instance si left join child ch on ch.id = si.child_id
      where ${inScope(scope, sql`coalesce(si.section, ch.section)`)}
        and exists (select 1 from capture c where c.sheet_instance_id = si.id and c.superseded_by is null)
        and not exists (select 1 from capture c join item_result r on r.capture_id = c.id
                        where c.sheet_instance_id = si.id and c.superseded_by is null)`,
  ]);

  const ids = [...new Set([...queue.filter((e) => !e.spot).map((e) => e.paper_id), ...signoff.map((s) => s.id)])];
  const refs = new Map((await paperRefs(ids)).map((r) => [r.id, r]));
  const ref = (id: string) => {
    const r = refs.get(id);
    return { subject: r?.subject ?? null, topic: r?.topic ?? null, topicName: r?.topic_name ?? null, section: r?.section ?? "", code: r?.code ?? "" };
  };
  const perPaper = new Map<string, { first: string; n: number }>();
  for (const e of queue.filter((e) => !e.spot)) {
    const at = perPaper.get(e.paper_id);
    perPaper.set(e.paper_id, { first: at?.first ?? e.id, n: (at?.n ?? 0) + 1 });
  }
  const reportsBy = new Map<string, { section: string; band: string; n: number }>();
  for (const r of reports) reportsBy.set(r.section, { section: r.section, band: r.band, n: (reportsBy.get(r.section)?.n ?? 0) + 1 });

  const src: Sources = {
    skills: skills.map((s) => ({ code: s.code, name: s.name, subject: s.subject, topic: s.topic, topicName: s.topic_name, gradeWords: g.name(s.grade), levels: s.levels })),
    home: home.filter((h) => h.proposed > 0).map((h) => ({ section: h.section, gradeWords: g.name(h.band), proposed: h.proposed })),
    check: [...perPaper].map(([paper, v]) => ({ paper, first: v.first, n: v.n, ...ref(paper) })),
    signoff: signoff.map((s) => ({ paper: s.id, n: s.n, ...ref(s.id) })),
    packs: packs.map((p) => ({ section: p.section, gradeWords: g.name(p.band), week: p.week, weekWords: weekWords(p.week), kind: p.kind, n: p.n, subject: null, topic: null, topicName: null })),
    untaught: tps.filter((t) => t.classes.some((c) => !c.taught)).map((t) => ({ topic: t.code, topicName: t.name, subject: t.subject, sections: t.classes.filter((c) => !c.taught).map((c) => c.section) })),
    generate: generate.map((x) => ({ topic: x.topic, topicName: x.topic_name, subject: x.subject, section: x.section })),
    reports: [...reportsBy.values()].map((r) => ({ section: r.section, gradeWords: g.name(r.band), n: r.n })),
    asks: asks.filter((a) => mayUse(me, "any_ask") || a.for_role === me.role).reduce((n, a) => n + a.n, 0),
    empty: empty[0]?.n ?? 0,
  };
  const label = new Map(offered.subjects.map((x) => [x.code, x.label]));
  return buildTasks(src, (c) => (c ? (label.get(c) ?? c) : ""));
});
