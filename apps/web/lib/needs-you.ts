import type { Session } from "./auth";
import { decidable, type Kind } from "./decides";
import { gradeWords } from "./queries";
import { type Waiting, waiting } from "./queries-today";
import { scopeOf } from "./scope";
import { weekWords } from "./week";

// What waits on a person, under the tab where it is done (goals/ui1-menu-and-today.yaml). Today lists these lines and
// the menu carries each tab's count, from this one list, so the two never disagree. Nimish, 2026-10-11: "I can't seem
// to actually find where I go and check the papers or questions for which human validation is required." Every line
// is counted in the classes the signed-in person sees (goals/f1b-my-classes-first.yaml, ADR 0073), and a line is theirs
// only when its decision is (goals/ux1-who-sees-what.yaml): an educator is never counted the coordinator's approvals.

export const TABS = ["Curriculum", "Assessments", "Children"] as const;
export type Tab = (typeof TABS)[number];
/** Today's order: the day's checking first, as the approved plan drew it; the menu keeps the school's order of work. */
export const TODAY_ORDER: readonly Tab[] = ["Assessments", "Curriculum", "Children"];

/** One thing to open: a class pack, a child's report — each a link of its own under its line. */
export type Item = { label: string; href: string; n?: number };
export type Line = {
  title: string;
  /** The decision it waits for; a person is shown it only when the decision is theirs (`people.decides`). */
  kind: Kind;
  n: number;
  words: string;
  /** Where it is done, and the button that opens it; a line of several items opens each item instead. */
  href?: string;
  action?: string;
  items?: Item[];
  /** Where the items past the first few are all listed (goals/ui6b-no-long-lists.yaml). */
  more?: string;
  /** Whether it is work waiting on a person, counted on the menu. A topic not taught yet is the school's choice. */
  waits: boolean;
};
export type NeedsYou = Record<Tab, Line[]>;

const KIND_WORDS: Record<string, string> = { practice: "class practice", assessment: "class assessment", focus: "home assessment" };

/** "Grade 2 · 2B": a class as an educator says it. */
export const classWords = (band: string, section: string) => `${gradeWords(band)} · ${section}`;
/** A count and its noun, said as a person says it: 1 child, 2 children. */
export const many = (n: number, one: string, more = `${one}s`) => `${n} ${n === 1 ? one : more}`;

export function linesOf(w: Waiting, may: (kind: Kind) => boolean = () => true): NeedsYou {
  const asks = w.asks.reduce((n, a) => n + a.n, 0);
  const packs = w.packs.reduce((n, p) => n + p.n, 0);
  const all: Record<Tab, Line[]> = {
    Assessments: [
      { title: "Answers to check", kind: "answers", n: w.answers, words: "the engine was not sure of these; each is shown beside the child's own writing", href: "/capture/check", action: "Check them", waits: true },
      { title: "Papers to sign off", kind: "papers", n: w.papers, words: "papers read whose answers no one has signed off; a child's record grows once they are", href: "/capture", action: "Sign them off", waits: true },
      {
        title: "Class papers to approve",
        kind: "class_papers",
        n: packs,
        words: "papers made for a class, waiting for a person before they print",
        items: w.packs.map((p) => ({
          label: `${classWords(p.band, p.section)} · ${KIND_WORDS[p.kind] ?? p.kind} · ${weekWords(p.week)}`,
          href: `/papers/approve?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`,
          n: p.n,
        })),
        more: "/papers/approve",
        waits: true,
      },
      { title: "Home assessments to approve", kind: "home_papers", n: w.nextPapers, words: "one for each child, made from their own record, not yet approved this week", href: "/make", action: "Approve them", waits: true },
      { title: "Scans that came back empty", kind: "papers", n: w.emptyReads, words: "papers read that gave back no answers at all: photograph or read them again", href: "/capture#nothing-came-back", action: "Look at them", waits: true },
    ],
    Curriculum: [
      { title: "Skills to approve", kind: "skills", n: w.skills, words: "skills whose words or levels the engine wrote or changed, each waiting for one approval", href: "/skill-sets/approve", action: "Review and approve", waits: true },
      { title: "Questions the engine drafted for you", kind: "asks", n: asks, words: "the engine's drafts of the taxonomy and its decisions, to agree with or correct", href: "/asks", action: "Answer them", waits: true },
      { title: "Topics not taught yet", kind: "topics", n: w.topics, words: "say a class has been taught a topic once it has; until then its skills are on none of that class's papers", href: "/#not-taught", action: "Say what is taught", waits: false },
    ],
    Children: [
      {
        title: "Parent reports to approve",
        kind: "reports",
        n: w.reports.length,
        words: "written for a parent and waiting for a person to read and approve",
        items: w.reports.map((r) => ({ label: `${classWords(r.band, r.section)} · Roll ${r.roll_no}`, href: `/growth/${r.child_id}/parent` })),
        // every report waiting on a person, in one list (goals/ui4b1-child-by-topic.yaml)
        href: "/growth/reports",
        action: "Open the list",
        more: "/growth/reports",
        waits: true,
      },
    ],
  };
  // a line with nothing waiting is left out, and one whose decision is someone else's: Today lists what needs this person
  return Object.fromEntries(TABS.map((t) => [t, all[t].filter((l) => l.n > 0 && may(l.kind))])) as NeedsYou;
}

/** What waits on this person: in their classes, decisions that are theirs, and the questions drafted for their role. */
export async function needsYou(me: Session): Promise<NeedsYou> {
  const [w, may] = await Promise.all([waiting(me.email, scopeOf(me)), decidable(me)]);
  const asks = me.role === "coordinator" ? w.asks : w.asks.filter((a) => a.for_role === me.role);
  return linesOf({ ...w, asks }, may);
}

/** {tab: what waits in it} for the menu, and Today's: every tab's together. */
export function counts(lines: NeedsYou): Record<Tab | "Today", number> {
  const per = Object.fromEntries(TABS.map((t) => [t, lines[t].filter((l) => l.waits).reduce((n, l) => n + l.n, 0)])) as Record<Tab, number>;
  return { ...per, Today: TABS.reduce((n, t) => n + per[t], 0) };
}
