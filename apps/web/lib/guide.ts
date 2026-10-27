import { cache } from "react";
import { sql } from "./db";
import { GROUPS, type MenuPage } from "./menu";
import { slugOf } from "./guide-path";
import start from "@/guide/start.json";
import workedOut from "@/guide/worked-out.json";
import words from "@/guide/words.json";
import problem from "@/guide/report-a-problem.json";
import steps from "@/guide/steps.json";
import today from "@/guide/pages/what-needs-doing.json";
import assessments from "@/guide/pages/assessments.json";
import approvePapers from "@/guide/pages/papers-to-approve.json";
import upload from "@/guide/pages/upload-papers.json";
import check from "@/guide/pages/check-answers.json";
import results from "@/guide/pages/class-results.json";
import reports from "@/guide/pages/parent-reports.json";
import across from "@/guide/pages/across-classes.json";
import curriculum from "@/guide/pages/curriculum.json";
import approveSkills from "@/guide/pages/skills-to-approve.json";
import bank from "@/guide/pages/question-bank.json";
import staff from "@/guide/pages/staff.json";
import school from "@/guide/pages/school.json";

// The Guide (goals/guide_for_educators.yaml). Nimish, 27 Oct 2026: "a guide page where everything is well explained ...
// so that people don't come to me". Its words are files in apps/web/guide/, held by packages/engine/tests/test_guide.py:
// one page per menu item, every route and button it names real, and no number, level, grade or state typed — each is a
// token, filled here from the rows in force, so the guide changes itself when the school changes a row.

export type Para = string;
export type Section = { id: string; title: string; paras: Para[] };
export type Article = { slug: string; title: string; purpose: string; sections: Section[] };
export type Area = { area: string; shows: string };
export type Button = { label: string; does: string; doesNot?: string };
export type Job = { id: string; title: string; steps: Para[] };
export type MenuGuide = { menu: string; forWhat: Para[]; layout: Area[]; jobs: Job[]; buttons: Button[]; note?: Para };
export type StepGuide = { name: string; who: string[]; sees: Para };
export type Want = { label: string; href: string };

const PAGES = [today, assessments, approvePapers, upload, check, results, reports, across, curriculum, approveSkills, bank, staff, school] as MenuGuide[];

export const START = start as { purpose: string; forWhat: Para[]; wants: Want[] };
export const ARTICLES = { "worked-out": workedOut, words, "report-a-problem": problem } as Record<string, Article>;
export const STEP_GUIDE = steps as Record<string, StepGuide>;

/** The menu's pages in its own order, each with its guide: one list, so the guide cannot reorder or skip the menu. */
export const MENU_GUIDE: { group: string; page: MenuPage; slug: string; guide: MenuGuide }[] = GROUPS.flatMap((g) =>
  g.pages.map((page) => ({ group: g.label, page, slug: slugOf(page.label), guide: PAGES.find((p) => p.menu === page.href)! })),
);

/** What the tokens of the guide's text are filled from: the threshold rows, and the school's grades, levels and states. */
export type Facts = {
  t: Record<string, number>;
  levels: string[];
  grades: { code: string; name: string }[];
  states: Record<string, string>;
  colours: Record<string, string>;
};

export const guideFacts = cache(async (): Promise<Facts> => {
  const [t, levels, grades, states, colours] = await Promise.all([
    sql<{ key: string; value: number }[]>`select key, value::float as value from threshold`,
    sql<{ code: string }[]>`select code from difficulty order by ord`,
    sql<{ code: string; name: string }[]>`select code, name from grade order by ord`,
    sql<{ code: string; words: string }[]>`select code, words from child_state order by ord`,
    sql<{ code: string; count_words: string }[]>`select code, count_words from state_colour order by ord`,
  ]);
  return {
    t: Object.fromEntries(t.map((r) => [r.key, r.value])),
    levels: levels.map((l) => l.code),
    grades,
    states: Object.fromEntries(states.map((s) => [s.code, s.words])),
    colours: Object.fromEntries(colours.map((c) => [c.code, c.count_words])),
  };
});

const and = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);

/** One token's words. `{t:key}` a threshold row (`|pct` as a share, `|hours`, `|days`… nothing else is added), `{levels}`,
 *  `{level:i}` (`-1` the hardest), `{grades}` (first to last), `{state:code}`, `{colour:code}`. An unknown one throws, so a
 *  row renamed or removed fails the page and its test rather than printing a gap. */
export function token(raw: string, f: Facts): string {
  const at = raw.indexOf(":");
  const [kind, rest] = at < 0 ? [raw, ""] : [raw.slice(0, at), raw.slice(at + 1)];
  const [arg, how] = rest.split("|");
  const need = <T,>(v: T | undefined): T => {
    if (v === undefined) throw new Error(`the guide names {${raw}}, which no row has`);
    return v;
  };
  if (kind === "t") {
    const v = need(f.t[arg]);
    return how === "pct" ? `${Math.round(v * 100)}%` : v.toLocaleString("en-IN");
  }
  if (kind === "levels") return and(f.levels);
  if (kind === "level") return need(f.levels.at(Number(arg)));
  if (kind === "grades") return `${need(f.grades[0]).name} to ${need(f.grades.at(-1)).name}`;
  if (kind === "state") return need(f.states[arg]);
  if (kind === "colour") return need(f.colours[arg]);
  throw new Error(`the guide names {${raw}}, which is not a kind of token`);
}

/** A paragraph in pieces: plain text, a button's label (`[[Label]]`), a link (`[words](/route)`). Tokens are filled first. */
export type Piece = { text: string } | { button: string } | { link: string; href: string };

export function pieces(p: Para, f: Facts): Piece[] {
  const filled = p.replace(/\{([^}]+)\}/g, (_, raw: string) => token(raw, f));
  const out: Piece[] = [];
  const re = /\[\[([^\]]+)\]\]|\[([^\]]+)\]\(([^)]+)\)/g;
  let at = 0;
  for (const m of filled.matchAll(re)) {
    if (m.index > at) out.push({ text: filled.slice(at, m.index) });
    out.push(m[1] ? { button: m[1] } : { link: m[2], href: m[3] });
    at = m.index + m[0].length;
  }
  if (at < filled.length) out.push({ text: filled.slice(at) });
  return out;
}

/** Every page of the guide in reading order: Start here, the menu's pages in the menu's order, then the rest. Each page's
 *  next step is the one after it, so the guide reads straight through. */
export const GUIDE_ORDER: { href: string; label: string }[] = [
  { href: "/guide", label: "Start here" },
  ...MENU_GUIDE.map((m) => ({ href: `/guide/${m.slug}`, label: m.page.label })),
  { href: "/guide/workflows", label: "The school's steps" },
  ...Object.values(ARTICLES).map((a) => ({ href: `/guide/${a.slug}`, label: a.title })),
];

export const nextAfter = (href: string) => GUIDE_ORDER[(GUIDE_ORDER.findIndex((g) => g.href === href) + 1) % GUIDE_ORDER.length];
