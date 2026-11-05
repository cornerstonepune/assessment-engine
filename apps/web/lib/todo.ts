import type { State } from "@/components/status-chip";
import { classWords, type MyVoice, SCHOOL_ZONE } from "./voice-types";
import { W } from "./voice-words";

// What needs doing, as one list of tasks (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026: "Key things that need
// to happen should be in a simple table with some red, amber, green notation ... Everything has to have its own set of
// approvals." One row is one thing on one item: an approval is the row's own action, never a button over all the rows. Pure:
// the sources are read in lib/queries-todo.ts, and this turns them into rows, so the rows can be tested without a database.

export type Ref = { subject: string | null; topic: string | null; topicName: string | null };
export type Kind = "check" | "signoff" | "classpaper" | "home" | "skill" | "report" | "ask" | "empty" | "taught" | "generate" | "record" | "note";

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
  // K2 voice notes (task M1-04): a note waits for her to confirm it; recording one is there when she needs it, never counted
  note: { what: W.kinds.note, state: "toConfirm", rank: 1 },
  record: { what: W.kinds.record, state: "toDo", rank: 2 },
};

export type Task = {
  id: string;
  kind: Kind;
  /** The classes it is about (none: it is the school's, or every class's). */
  sections: string[];
  /** What the page it opens must show, in words: a test reads it (goals/nav3_what_needs_doing.yaml). */
  shows: string;
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
  /** her K2 classes and her notes waiting (lib/voice.ts), none while voice notes are switched off */
  voice?: MyVoice | null;
};

export const count = (n: number, one: string, more = `${one}s`) => `${n.toLocaleString("en-IN")} ${n === 1 ? one : more}`;
const KIND_WORDS: Record<string, string> = { practice: "class practice", assessment: "class assessment", focus: "home assessment" };

export function buildTasks(src: Sources, subjectLabel: (code: string | null) => string): Task[] {
  const out: Task[] = [];
  const add = (kind: Kind, id: string, ref: Ref, where: string[], many: string, href: string, action: string, shows: string, sections: string[] = []) =>
    out.push({
      id: `${kind}:${id}`,
      kind,
      sections,
      shows,
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
  for (const s of src.skills) add("skill", s.code, s, [s.gradeWords, s.name], count(s.levels, "level"), `/skill-sets/${s.code}`, "Read and approve", s.name);
  for (const h of src.home) add("home", h.section, none, [h.gradeWords, h.section], count(h.proposed, "child", "children"), `/make/${encodeURIComponent(h.section)}`, "Open the class", h.section, [h.section]);
  for (const c of src.check) add("check", c.paper, c, [c.section, c.code], count(c.n, "answer"), `/capture/check?id=${c.first}`, "Check this paper", c.code, [c.section]);
  for (const p of src.signoff) add("signoff", p.paper, p, [p.section, p.code], count(p.n, "answer"), `/capture/${p.paper}`, "Sign it off", p.section, [p.section]);
  for (const p of src.packs)
    add("classpaper", `${p.section}|${p.week}|${p.kind}`, p, [p.gradeWords, p.section, KIND_WORDS[p.kind] ?? p.kind, p.weekWords], count(p.n, "paper"), `/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`, "Open the papers", p.section, [p.section]);
  for (const r of src.reports) add("report", r.section, none, [r.gradeWords, r.section], count(r.n, "report"), `/growth/reports?class=${encodeURIComponent(r.section)}`, "Read the reports", r.section, [r.section]);
  for (const t of src.untaught)
    add("taught", t.topic, { subject: t.subject, topic: t.topic, topicName: t.topicName }, [t.sections.length > 3 ? `${t.sections.length} classes` : t.sections.join(", ")], count(t.sections.length, "class", "classes"), `/?topic=${encodeURIComponent(t.topic)}`, "Mark as taught", t.topicName, t.sections);
  for (const g of src.generate)
    add("generate", `${g.topic}|${g.section}`, { subject: g.subject, topic: g.topic, topicName: g.topicName }, [g.section], "none yet", `/papers/make?topic=${encodeURIComponent(g.topic)}&section=${encodeURIComponent(g.section)}`, "Make one", g.section, [g.section]);
  const klass = new Map((src.voice?.classes ?? []).map((c) => [c.id, classWords(c)]));
  // with recording off (D-065) a class's row opens the form: no Record, no microphone
  const recording = src.voice?.recording ?? false;
  for (const c of src.voice?.classes ?? [])
    add("record", c.id, none, [klass.get(c.id)!], "", recording ? `/voice/record?class=${c.id}` : `/voice/form?class=${c.id}`, recording ? W.record.start : W.fillForm, klass.get(c.id)!, [klass.get(c.id)!]);
  for (const n of src.voice?.notes ?? []) {
    const where = klass.get(n.class_id) ?? "";
    add("note", n.id, none, [where, heardAt(n.received_at)], "1 note", `/voice/notes/${n.id}`, n.status === "received" ? W.confirm.reading : W.confirm.button, where, where ? [where] : []);
    if (n.status === "received") out[out.length - 1].state = "reading";
  }
  if (src.asks) add("ask", "drafted", none, [], count(src.asks, "question"), "/asks", "Open the questions", "Questions to answer");
  if (src.empty) add("empty", "scans", none, [], count(src.empty, "scan"), "/capture#nothing-came-back", "Look at the scans", "Upload papers");
  return out.sort((a, b) => KINDS[a.kind].rank - KINDS[b.kind].rank || (a.subject ?? "~").localeCompare(b.subject ?? "~") || (a.topicName ?? "").localeCompare(b.topicName ?? "") || a.where.localeCompare(b.where, "en", { numeric: true }));
}
const none: Ref = { subject: null, topic: null, topicName: null };

/** When a note reached us, as she reads it: "10:42" today, else "3 Nov 10:42" (the school's clock). */
function heardAt(iso: string): string {
  const at = new Date(iso);
  const day = (d: Date) => d.toLocaleDateString("en-IN", { timeZone: SCHOOL_ZONE, day: "numeric", month: "short" });
  const time = at.toLocaleTimeString("en-IN", { timeZone: SCHOOL_ZONE, hour: "2-digit", minute: "2-digit", hour12: false });
  return day(at) === day(new Date()) ? time : `${day(at)} ${time}`;
}

/** The topic filter that means "the tasks of no topic" (a class's papers, the questions). */
export const NO_TOPIC = "none";
export type Filters = { subject?: string; section?: string; kind?: string };

/** A task with no subject (a class's home papers, a question) belongs to every subject's view, and one of no class to every class's. */
export function filterTasks(tasks: readonly Task[], f: Filters, mySubjects: readonly string[] | null): Task[] {
  return tasks.filter(
    (t) =>
      (!mySubjects || !t.subject || mySubjects.includes(t.subject)) &&
      (!f.subject || !t.subject || t.subject === f.subject) &&
      (!f.section || !t.sections.length || t.sections.includes(f.section)) &&
      (!f.kind || t.kind === f.kind),
  );
}

/** The kinds of task a person does together, each with the page that does that work. Nimish, 26 Oct 2026: "different types of
 *  things that you need to do ... skills to be checked or topics to be marked ... Everything is very well sequenced." In the order
 *  the work happens (docs/sources/assessment-workflow-v1.md): the skills (N1), what was taught (N4), the papers made and approved
 *  (N5-N7), the scans read (N8), the answers checked (N9), the home papers (N11), the reports (N12). */
export type GroupKey = "record" | "notes" | "skills" | "asks" | "taught" | "generate" | "classpapers" | "scans" | "answers" | "home" | "reports";
/** `of`: what one row is, for the count on the group's line ("3 papers"). */
export type Group = {
  key: GroupKey;
  title: string;
  of: readonly [string, string];
  kinds: readonly Kind[];
  home: string;
  /** a title that follows its rows (the K2 group reads "Fill the form" while recording is off) */
  titleOf?: (tasks: readonly Task[]) => string;
};
export const TODO_GROUPS: readonly Group[] = [
  // K2 first: a note is recorded after the activity and confirmed the same day (shown only while voice notes are on)
  { key: "record", title: W.groups.record, of: ["class", "classes"], kinds: ["record"], home: "/today?open=record", titleOf: (ts) => (ts.every((t) => t.href.startsWith("/voice/form")) ? W.groups.form : W.groups.record) },
  { key: "notes", title: W.groups.notes, of: ["to confirm", "to confirm"], kinds: ["note"], home: "/today?open=notes" },
  { key: "skills", title: "Skills to approve", of: ["skill", "skills"], kinds: ["skill"], home: "/skill-sets/approve" },
  { key: "asks", title: "Questions to answer", of: ["question", "questions"], kinds: ["ask"], home: "/asks" },
  { key: "taught", title: "Topics to mark as taught", of: ["topic", "topics"], kinds: ["taught"], home: "/" },
  { key: "generate", title: "Assessments to make", of: ["assessment", "assessments"], kinds: ["generate"], home: "/papers/make" },
  { key: "classpapers", title: "Class papers to approve", of: ["class paper", "class papers"], kinds: ["classpaper"], home: "/papers/approve" },
  { key: "scans", title: "Papers to read again", of: ["scan", "scans"], kinds: ["empty"], home: "/capture" },
  { key: "answers", title: "Answers to check", of: ["paper", "papers"], kinds: ["check", "signoff"], home: "/capture/check" },
  { key: "home", title: "Home assessments to approve", of: ["class", "classes"], kinds: ["home"], home: "/make" },
  { key: "reports", title: "Parent reports to approve", of: ["class", "classes"], kinds: ["report"], home: "/growth/reports" },
];

export type Section = { group: Group; title: string; tasks: Task[]; state: State; next: Task };

/** The groups that have something waiting, in order. A group is as urgent as its most urgent row; its next action is its first row's. */
export function sectionsOf(tasks: readonly Task[]): Section[] {
  return TODO_GROUPS.flatMap((group) => {
    const mine = tasks.filter((t) => group.kinds.includes(t.kind));
    if (!mine.length) return [];
    const worst = mine.reduce((a, t) => (KINDS[t.kind].rank < KINDS[a.kind].rank ? t : a));
    return [{ group, title: group.titleOf?.(mine) ?? group.title, tasks: mine, state: worst.state, next: mine[0] }];
  });
}

/** The count the menu carries: what the educator must act on (red and amber), not what can wait. */
export const waitingCount = (tasks: readonly Task[]) => tasks.filter((t) => KINDS[t.kind].rank < 2).length;
