import type { State } from "@/components/status-chip";

// What needs doing, as one list of tasks (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026: "Key things that need
// to happen should be in a simple table with some red, amber, green notation ... Everything has to have its own set of
// approvals." One row is one thing on one item: an approval is the row's own action, never a button over all the rows. Pure:
// the sources are read in lib/queries-todo.ts, and this turns them into rows, so the rows can be tested without a database.

export type Ref = { subject: string | null; topic: string | null; topicName: string | null };
export type Kind = "check" | "signoff" | "classpaper" | "home" | "skill" | "report" | "ask" | "empty" | "taught" | "generate";

/** What a kind of task is called, how urgent it is, and the chip that says so (red: do now; amber: this week; green: when ready). */
export const KINDS: Record<Kind, { what: string; state: State; rank: number }> = {
  check: { what: "Check answers", state: "doNow", rank: 0 },
  empty: { what: "Read a scan again", state: "doNow", rank: 0 },
  signoff: { what: "Sign off a paper", state: "doSoon", rank: 1 },
  classpaper: { what: "Approve a class paper", state: "doSoon", rank: 1 },
  home: { what: "Approve a home assessment", state: "doSoon", rank: 1 },
  skill: { what: "Approve a skill", state: "doSoon", rank: 1 },
  report: { what: "Approve a parent report", state: "doSoon", rank: 1 },
  ask: { what: "Answer a question", state: "doSoon", rank: 1 },
  taught: { what: "Mark a topic taught", state: "whenReady", rank: 2 },
  generate: { what: "Generate an assessment", state: "whenReady", rank: 2 },
};

export type Task = {
  id: string;
  kind: Kind;
  state: State;
  what: string;
  subject: string | null;
  topic: string | null;
  topicName: string | null;
  /** "Maths · Addition · 2B", as a person reads where it is. */
  where: string;
  /** How many, in words: "12 answers". */
  many: string;
  href: string;
  action: string;
};

export type Sources = {
  skills: (Ref & { code: string; name: string; gradeWords: string; levels: number })[];
  home: { section: string; gradeWords: string; proposed: number }[];
  check: (Ref & { paper: string; first: string; code: string; section: string; n: number })[];
  signoff: (Ref & { paper: string; code: string; section: string; n: number })[];
  packs: (Ref & { section: string; gradeWords: string; week: string; weekWords: string; kind: string; n: number })[];
  untaught: { topic: string; topicName: string; subject: string | null; sections: string[] }[];
  generate: { topic: string; topicName: string; subject: string | null; section: string }[];
  reports: { section: string; gradeWords: string; n: number }[];
  asks: number;
  empty: number;
};

export const count = (n: number, one: string, more = `${one}s`) => `${n.toLocaleString("en-IN")} ${n === 1 ? one : more}`;
const KIND_WORDS: Record<string, string> = { practice: "class practice", assessment: "class assessment", focus: "home assessment" };

export function buildTasks(src: Sources, subjectLabel: (code: string | null) => string): Task[] {
  const out: Task[] = [];
  const add = (kind: Kind, id: string, ref: Ref, where: string[], many: string, href: string, action: string) =>
    out.push({
      id: `${kind}:${id}`,
      kind,
      state: KINDS[kind].state,
      what: KINDS[kind].what,
      subject: ref.subject,
      topic: ref.topic,
      topicName: ref.topicName,
      where: [ref.subject ? subjectLabel(ref.subject) : null, ref.topicName, ...where].filter(Boolean).join(" · "),
      many,
      href,
      action,
    });
  for (const s of src.skills) add("skill", s.code, s, [s.gradeWords, s.name], count(s.levels, "level"), `/skill-sets/${s.code}`, "Read and approve");
  for (const h of src.home) add("home", h.section, none, [h.gradeWords, h.section], count(h.proposed, "child", "children"), `/make/${encodeURIComponent(h.section)}`, "Open the class");
  for (const c of src.check) add("check", c.paper, c, [c.section, c.code], count(c.n, "answer"), `/capture/check?id=${c.first}`, "Check this paper");
  for (const p of src.signoff) add("signoff", p.paper, p, [p.section, p.code], count(p.n, "answer"), `/capture/${p.paper}`, "Sign it off");
  for (const p of src.packs)
    add("classpaper", `${p.section}|${p.week}|${p.kind}`, p, [p.gradeWords, p.section, KIND_WORDS[p.kind] ?? p.kind, p.weekWords], count(p.n, "paper"), `/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`, "Open the papers");
  for (const r of src.reports) add("report", r.section, none, [r.gradeWords, r.section], count(r.n, "report"), `/growth/reports?class=${encodeURIComponent(r.section)}`, "Read the reports");
  for (const t of src.untaught)
    add("taught", t.topic, { subject: t.subject, topic: t.topic, topicName: t.topicName }, [t.sections.length > 3 ? `${t.sections.length} classes` : t.sections.join(", ")], count(t.sections.length, "class", "classes"), `/taught?topic=${encodeURIComponent(t.topic)}`, "Open the topic");
  for (const g of src.generate)
    add("generate", `${g.topic}|${g.section}`, { subject: g.subject, topic: g.topic, topicName: g.topicName }, [g.section], "none yet", `/papers/make?topic=${encodeURIComponent(g.topic)}&section=${encodeURIComponent(g.section)}`, "Make one");
  if (src.asks) add("ask", "drafted", none, [], count(src.asks, "question"), "/asks", "Open the questions");
  if (src.empty) add("empty", "scans", none, [], count(src.empty, "scan"), "/capture#nothing-came-back", "Look at the scans");
  return out.sort((a, b) => KINDS[a.kind].rank - KINDS[b.kind].rank || (a.subject ?? "~").localeCompare(b.subject ?? "~") || (a.topicName ?? "").localeCompare(b.topicName ?? "") || a.where.localeCompare(b.where, "en", { numeric: true }));
}
const none: Ref = { subject: null, topic: null, topicName: null };

export type Filters = { subject?: string; topic?: string; kind?: string };

/** A task with no subject (a class's home papers, a question) belongs to every subject's view. */
export function filterTasks(tasks: readonly Task[], f: Filters, mySubjects: readonly string[] | null): Task[] {
  return tasks.filter(
    (t) =>
      (!mySubjects || !t.subject || mySubjects.includes(t.subject)) &&
      (!f.subject || !t.subject || t.subject === f.subject) &&
      (!f.topic || t.topic === f.topic) &&
      (!f.kind || t.kind === f.kind),
  );
}

/** Subject, then topic, each in order of first appearance (so red comes first); a task of no topic is under "Across topics". */
export function groupTasks(tasks: readonly Task[], subjectLabel: (code: string | null) => string): { subject: string; topics: { topic: string; tasks: Task[] }[] }[] {
  const subjects = new Map<string, Map<string, Task[]>>();
  for (const t of tasks) {
    const s = t.subject ? subjectLabel(t.subject) : "Across subjects";
    const topics = subjects.get(s) ?? new Map<string, Task[]>();
    const k = t.topicName ?? "Across topics";
    topics.set(k, [...(topics.get(k) ?? []), t]);
    subjects.set(s, topics);
  }
  return [...subjects].map(([subject, topics]) => ({ subject, topics: [...topics].map(([topic, ts]) => ({ topic, tasks: ts })) }));
}

/** The count the menu carries: what the educator must act on (red and amber), not what can wait. */
export const waitingCount = (tasks: readonly Task[]) => tasks.filter((t) => KINDS[t.kind].rank < 2).length;
