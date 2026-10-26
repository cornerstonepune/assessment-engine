/**
 * What needs doing as groups (goals/nav3_what_needs_doing.yaml). No browser, no database: the kinds of task, their order, how
 * urgent a group is, and that every link a task makes names a page that exists. Nimish, 26 Oct 2026: "Everything is very well
 * sequenced with clarity", "What Needs Doing essentially connects to each of the other sub-tabs."
 */
import { expect, test } from "@playwright/test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { buildTasks, KINDS, sectionsOf, TODO_GROUPS, type Kind, type Sources } from "../lib/todo";
import { GROUPS, groupOf, locate } from "../lib/menu";

const SRC: Sources = {
  skills: [{ code: "NUM.OPS.01", name: "Add within 20", subject: "NUM", topic: "ADDSUB", topicName: "Addition", gradeWords: "Grade 1", levels: 4 }],
  home: [{ section: "2B", gradeWords: "Grade 2", proposed: 12 }],
  check: [{ paper: "p1", first: "r1", code: "CSAAAAAA", section: "2B", n: 5, subject: "NUM", topic: "MUL", topicName: "Multiplication" }],
  signoff: [{ paper: "p2", code: "CSBBBBBB", section: "2B", n: 3, subject: "NUM", topic: "MUL", topicName: "Multiplication" }],
  packs: [{ section: "2B", gradeWords: "Grade 2", week: "2026-W43", weekWords: "week 43", kind: "assessment", n: 4, subject: null, topic: null, topicName: null }],
  untaught: [{ topic: "DIV", topicName: "Division", subject: "NUM", sections: ["2B", "2C"] }],
  generate: [{ topic: "MUL", topicName: "Multiplication", subject: "NUM", section: "2B" }],
  reports: [{ section: "2B", gradeWords: "Grade 2", n: 7 }],
  asks: 2,
  empty: 1,
};
const tasks = buildTasks(SRC, (c) => c ?? "");

test("every kind of task is in exactly one group, and the groups follow the order the work happens", () => {
  const kinds = Object.keys(KINDS) as Kind[];
  for (const k of kinds) expect(TODO_GROUPS.filter((g) => g.kinds.includes(k)).map((g) => g.key), k).toHaveLength(1);
  expect(TODO_GROUPS.map((g) => g.key)).toEqual(["skills", "asks", "taught", "generate", "classpapers", "scans", "answers", "home", "reports"]);
  expect(sectionsOf(tasks).map((s) => s.group.key)).toEqual(TODO_GROUPS.map((g) => g.key));
});

test("a group is as urgent as its worst row, and its next action is its first row's", () => {
  const answers = sectionsOf(tasks).find((s) => s.group.key === "answers")!;
  expect(answers.tasks.map((t) => t.kind).sort()).toEqual(["check", "signoff"]);
  expect(answers.state).toBe("doNow");
  expect(answers.next).toBe(answers.tasks[0]);
  expect(sectionsOf(tasks).find((s) => s.group.key === "generate")!.state).toBe("whenReady");
  expect(sectionsOf([])).toEqual([]);
});

// a link names a page when a page file answers its path: static folders, [params], and the route groups in brackets
const APP = path.resolve(__dirname, "../app");
function routeExists(href: string, dir = path.join(APP, "(app)")): boolean {
  const parts = href.split(/[?#]/)[0].split("/").filter(Boolean);
  if (!parts.length) return existsSync(path.join(dir, "page.tsx"));
  const [head, ...rest] = parts;
  const here = readdirSync(dir, { withFileTypes: true }).filter((d) => d.isDirectory());
  return [head, ...here.map((d) => d.name).filter((n) => /^\[[^.\]]+\]$/.test(n))].some((n) => {
    const next = path.join(dir, n);
    return existsSync(next) && (rest.length ? routeExists(rest.join("/"), next) : existsSync(path.join(next, "page.tsx")));
  });
}

test("every group's home and every row's link names a page that exists", () => {
  for (const g of TODO_GROUPS) expect(routeExists(g.home), `${g.key} -> ${g.home}`).toBe(true);
  for (const t of tasks) expect(routeExists(t.href), `${t.id} -> ${t.href}`).toBe(true);
  expect(routeExists("/no-such-page")).toBe(false);
});

test("a group's home is a page of the menu, and a row opens a page of the group that does that work", () => {
  for (const g of TODO_GROUPS) expect(locate(g.home)?.group, g.home).toBeDefined();
  for (const t of tasks) expect(locate(t.href.split(/[?#]/)[0])?.group, t.href).toBeDefined();
});

test("Teaching is not in the menu, and nothing links to its address", () => {
  expect(GROUPS.map((g) => g.label)).not.toContain("Teaching");
  expect(groupOf("/taught")).toBeUndefined();
  const links: string[] = [];
  const walk = (dir: string) =>
    readdirSync(dir, { withFileTypes: true }).forEach((d) => {
      const f = path.join(dir, d.name);
      if (d.isDirectory()) walk(f);
      else if (/\.tsx?$/.test(d.name) && /["'`]\/taught/.test(readFileSync(f, "utf8"))) links.push(f);
    });
  walk(APP);
  walk(path.resolve(__dirname, "../lib"));
  walk(path.resolve(__dirname, "../components"));
  expect(links, "a file that still links to /taught").toEqual([]);
});

test("the top bar has no Viewing control and nothing keeps its choice", () => {
  const read = (f: string) => readFileSync(path.resolve(__dirname, "..", f), "utf8");
  expect(read("components/top-bar.tsx")).not.toMatch(/Viewing|data-viewing|bar-class|bar-subject/);
  expect(read("components/shell.tsx")).not.toMatch(/Viewing|isBroad/);
  expect(read("lib/auth-actions.ts")).not.toMatch(/export async function choose/);
  expect(read("lib/auth.ts")).not.toMatch(/cs_classes|cs_subject/);
});
