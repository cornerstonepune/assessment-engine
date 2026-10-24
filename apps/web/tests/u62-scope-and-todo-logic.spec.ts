/**
 * U62 — the logic behind the top navigation, What needs doing and Teaching (goals/nav_teacher_scope_and_todo.yaml). No
 * browser and no database: scope per role, the task rows built from the sources, the topic flow, and the rule that no
 * page offers one button over every row. Nimish, 24 Oct 2026: "Everything has to have its own set of approvals."
 */
import { expect, test } from "@playwright/test";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { isBroad, subjectNow, subjectsFor, viewingWords } from "../lib/viewing";
import { buildTasks, filterTasks, groupTasks, KINDS, waitingCount, type Sources } from "../lib/todo";
import { classResult, topicFlow, topicStatuses } from "../lib/topic-flow";
import { groupOf, GROUPS, tabsOf } from "../lib/menu";

const SUBJECTS = [
  { code: "NUM", label: "Maths" },
  { code: "ENG", label: "English" },
];

test.describe("scope per role", () => {
  test("an educator with one class and one subject sees that alone and is offered no choice", () => {
    const p = { classes: ["2B"], subjects: ["NUM"] };
    expect(isBroad(p)).toBe(false);
    expect(subjectsFor(p, SUBJECTS).map((s) => s.code)).toEqual(["NUM"]);
    expect(subjectNow(p, SUBJECTS, "ENG")?.code).toBe("NUM");
  });
  test("a coordinator (every class) or a person with two subjects chooses what to view", () => {
    expect(isBroad({ classes: [], subjects: [] })).toBe(true);
    expect(isBroad({ classes: ["2B"], subjects: ["NUM", "ENG"] })).toBe(true);
    expect(subjectNow({ classes: [], subjects: [] }, SUBJECTS, "ENG")?.code).toBe("ENG");
    expect(subjectNow({ classes: [], subjects: [] }, SUBJECTS, null)?.code).toBe("NUM");
  });
  test("a subject the staff list names that the school lacks is ignored; none named is every subject", () => {
    expect(subjectsFor({ subjects: ["ART"] }, SUBJECTS)).toHaveLength(2);
    expect(subjectsFor({}, SUBJECTS)).toHaveLength(2);
  });
  test("the Viewing control says its scope in words", () => {
    expect(viewingWords("Maths", null)).toBe("Maths · every class");
    expect(viewingWords("Maths", ["2B", "2C"])).toBe("Maths · 2B, 2C");
    expect(viewingWords(undefined, ["1A", "1B", "1C", "1D"])).toBe("4 classes");
  });
});

const SRC: Sources = {
  skills: [
    { code: "NUM.OPS.01", name: "Add within 20", subject: "NUM", topic: "ADDSUB", topicName: "Addition & subtraction", gradeWords: "Grade 1", levels: 4 },
    { code: "NUM.OPS.02", name: "Subtract within 20", subject: "NUM", topic: "ADDSUB", topicName: "Addition & subtraction", gradeWords: "Grade 1", levels: 4 },
    { code: "ENG.READ.01", name: "Read a passage", subject: "ENG", topic: "ENG.READ", topicName: "Reading", gradeWords: "Grade 1", levels: 3 },
  ],
  home: [{ section: "2B", gradeWords: "Grade 2", proposed: 12 }],
  check: [{ paper: "p1", first: "r1", code: "CSAAAAAA", section: "2B", n: 5, subject: "NUM", topic: "MUL", topicName: "Multiplication" }],
  signoff: [{ paper: "p2", code: "CSBBBBBB", section: "2B", n: 3, subject: "NUM", topic: "MUL", topicName: "Multiplication" }],
  packs: [],
  untaught: [{ topic: "DIV", topicName: "Division", subject: "NUM", sections: ["2B", "2C"] }],
  generate: [{ topic: "MUL", topicName: "Multiplication", subject: "NUM", section: "2B" }],
  reports: [{ section: "2B", gradeWords: "Grade 2", n: 7 }],
  asks: 2,
  empty: 0,
};
const label = (c: string | null) => SUBJECTS.find((s) => s.code === c)?.label ?? "";

test.describe("what needs doing", () => {
  const tasks = buildTasks(SRC, label);
  test("one row per item, each with its own action that opens that item", () => {
    expect(tasks.filter((t) => t.kind === "skill")).toHaveLength(3);
    for (const t of tasks) {
      expect(t.href, t.id).toMatch(/^\//);
      expect(t.action, t.id).not.toMatch(/\b(all|them|these|every)\b/i);
    }
    expect(tasks.find((t) => t.id === "skill:NUM.OPS.02")?.href).toBe("/skill-sets/NUM.OPS.02");
    expect(tasks.find((t) => t.kind === "check")?.href).toBe("/capture/check?id=r1");
    expect(tasks.find((t) => t.kind === "signoff")?.href).toBe("/capture/p2");
  });
  test("red first, then amber, then green; every task is one of the school's named kinds", () => {
    const ranks = tasks.map((t) => KINDS[t.kind].rank);
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b));
    expect(tasks[0].state).toBe("doNow");
    expect(tasks.at(-1)?.state).toBe("whenReady");
    expect(tasks.find((t) => t.kind === "taught")?.what).toBe("Mark a topic taught");
  });
  test("where says subject, topic and class; no row says 'approve all'", () => {
    expect(tasks.find((t) => t.kind === "check")?.where).toBe("Maths · Multiplication · 2B · CSAAAAAA");
    expect(tasks.some((t) => /approve (all|them|every)/i.test(`${t.what} ${t.action}`))).toBe(false);
  });
  test("a person's subjects narrow the rows; a row of no subject stays", () => {
    const eng = filterTasks(tasks, {}, ["ENG"]);
    expect(eng.every((t) => t.subject === "ENG" || t.subject === null)).toBe(true);
    expect(eng.some((t) => t.kind === "home")).toBe(true);
    expect(filterTasks(tasks, { subject: "NUM", kind: "skill" }, null).map((t) => t.id)).toEqual(["skill:NUM.OPS.01", "skill:NUM.OPS.02"]);
    expect(filterTasks(tasks, { topic: "ADDSUB" }, null)).toHaveLength(2);
  });
  test("grouped by subject then topic, red first inside", () => {
    const g = groupTasks(tasks, label);
    expect(g[0].subject).toBe("Maths");
    expect(g.flatMap((s) => s.topics.map((t) => t.topic))).toContain("Across topics");
  });
  test("the menu's count is what the educator must act on, not what can wait", () => {
    expect(waitingCount(tasks)).toBe(tasks.filter((t) => t.state !== "whenReady").length);
  });
});

test.describe("topic flow", () => {
  const base = { skills: { total: 3, approved: 3 }, taughtAt: "2026-10-05T00:00:00Z" };
  test("the baseline is the first class assessment; home papers count children and repeats", () => {
    const f = topicFlow({
      ...base,
      sheets: [
        { kind: "assessment", child: "a", at: "2026-10-08T00:00:00Z" },
        { kind: "assessment", child: "b", at: "2026-10-06T00:00:00Z" },
        { kind: "focus", child: "a", at: "2026-10-10T00:00:00Z" },
        { kind: "focus", child: "a", at: "2026-10-17T00:00:00Z" },
        { kind: "focus", child: "b", at: "2026-10-17T00:00:00Z" },
        { kind: "practice", child: "a", at: "2026-10-01T00:00:00Z" },
        { kind: "practice", child: "a", at: "2026-10-20T00:00:00Z" },
      ],
    });
    expect(f.skills.ready).toBe(true);
    expect(f.baseline).toEqual({ done: true, at: "2026-10-06T00:00:00Z" });
    expect(f.home).toEqual({ papers: 3, children: 2, repeat: 1 });
    expect(f.practice.papers).toBe(1);
  });
  test("a topic not yet taught has no practice, and no baseline until one is made", () => {
    const f = topicFlow({ skills: { total: 2, approved: 1 }, sheets: [{ kind: "practice", child: null, at: "2026-10-20T00:00:00Z" }], taughtAt: null });
    expect(f.skills.ready).toBe(false);
    expect(f.baseline.done).toBe(false);
    expect(f.practice.papers).toBe(0);
  });
  test("the class result is the colour most children hold, the worse on a tie", () => {
    expect(classResult({ red: 0, amber: 0, green: 0 })).toBe("noResult");
    expect(classResult({ red: 1, amber: 1, green: 5 })).toBe("fine");
    expect(classResult({ red: 2, amber: 2, green: 1 })).toBe("needsHelp");
    expect(classResult({ red: 0, amber: 2, green: 2 })).toBe("gettingThere");
  });
  test("taught, teaching now, next (the first not taught of its subject), not taught", () => {
    const s = topicStatuses(
      [
        { code: "A", subject: "NUM", taught: true },
        { code: "B", subject: "NUM", taught: false },
        { code: "C", subject: "NUM", taught: false },
        { code: "E", subject: "ENG", taught: false },
      ],
      new Set(["B"]),
    );
    expect([...s]).toEqual([["A", "taught"], ["B", "teachingNow"], ["C", "nextUp"], ["E", "nextUp"]]);
  });
});

test.describe("the menu", () => {
  test("five groups, in order, and every sub-page belongs to one", () => {
    expect(GROUPS.map((g) => g.label)).toEqual(["What needs doing", "Teaching", "Assessments", "Results", "Setup"]);
    expect(groupOf("/papers/approve")?.label).toBe("Assessments");
    expect(groupOf("/capture/check")?.label).toBe("Assessments");
    expect(groupOf("/skill-sets/approve")?.label).toBe("Setup");
    expect(groupOf("/taught")?.label).toBe("Teaching");
    expect(groupOf("/growth/class/2B")?.label).toBe("Results");
    expect(tabsOf("/papers").map((t) => t.label)).toContain("Papers to approve");
    expect(tabsOf("/today")).toEqual([]);
  });
});

test.describe("no approve-all", () => {
  // the build fails if a page offers one button over every row (Nimish, 24 Oct 2026); pages still on workflows.json
  // `ux.approveAll` are the debt, and the list only shrinks
  const root = path.resolve(__dirname, "../app");
  const files = (dir: string): string[] =>
    readdirSync(dir).flatMap((f) => {
      const p = path.join(dir, f);
      return statSync(p).isDirectory() ? files(p) : /\.tsx$/.test(f) ? [p] : [];
    });
  const BAD = /\bApprove\s+(all|these|them|every)\b|\bApprove\s+\$\{[^}]*\}\s+\w*|\bApprove\s*\{[^}]*"(all|these)"|\bMake and approve/;
  const debt: string[] = JSON.parse(readFileSync(path.resolve(__dirname, "../../../workflows.json"), "utf8")).ux.approveAll ?? [];
  test("no page has an 'approve all' control", () => {
    const hits = files(root)
      .filter((f) => BAD.test(readFileSync(f, "utf8")))
      .map((f) => path.relative(root, f).split(path.sep).join("/"));
    expect(hits.filter((h) => !debt.includes(h)), "a page with an approve-all control").toEqual([]);
    expect(debt.filter((d) => !hits.includes(d)), "a page that no longer has one must leave ux.approveAll").toEqual([]);
  });
});
