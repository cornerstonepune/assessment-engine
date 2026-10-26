/**
 * The Assessments page's logic (goals/asm_assessments_page.yaml): a name built from the sheet's own code, the steps an
 * assessment has been through and the one thing to do next, and a file listed against its assessment. No page is opened.
 */
import { expect, test } from "@playwright/test";
import {
  actionOf,
  actionOfSig,
  builtName,
  matchFiles,
  nameOf,
  sigOf,
  sigsFor,
  stepCells,
  standingWords,
  type Counts,
} from "../lib/assessment-steps";

const KINDS = { assessment: "Class assessment", focus: "Home assessment" };
const by = (o: Partial<Counts["by"]>): Counts["by"] => ({ made: 0, printed: 0, scanned: 0, checked: 0, "signed off": 0, ...o });
const cls = (o: Partial<Counts["by"]>, unread = 0): Counts => ({ by: by(o), unread, home: false });

const facts = { title: "", topics: [] as string[], skills: [] as string[], levels: [] as string[], kinds: KINDS };

test("an assessment is named as a teacher would say it: topic, skill, level, kind, class and day; the composition is never the title", () => {
  expect(
    builtName({
      ...facts,
      topics: ["Addition & subtraction"],
      skills: ["2-digit + 2-digit"],
      levels: ["Easy"],
      kind: "focus",
      classWords: "Grade 1 · 1A",
      day: "2026-10-12",
    }),
  ).toBe("Addition & subtraction · 2-digit + 2-digit · Easy · Home assessment · Grade 1 · 1A · 12-Oct-2026");
  // three or more skills are counted, never listed; levels that differ are left out; two topics are joined, more are "mixed"
  expect(
    builtName({
      ...facts,
      topics: ["Addition & subtraction"],
      skills: ["a", "b", "c", "d"],
      levels: ["Easy", "Hard"],
      kind: "focus",
      classWords: null,
      day: null,
    }),
  ).toBe("Addition & subtraction · 4 skills · Home assessment");
  expect(builtName({ ...facts, topics: ["A", "B", "C"], skills: ["x"], kind: "assessment", classWords: null, day: null })).toBe(
    "Mixed topics · x · Class assessment",
  );
  // a part the sheet does not carry is left out; a paper with no skill is named by its own title, and not told its kind twice
  expect(builtName({ ...facts, title: "Home assessments", kind: "focus", classWords: null, day: null })).toBe("Home assessments");
  expect(builtName({ ...facts, title: "Home assessments", kind: "focus", classWords: "Grade 2", day: "2026-10-24" })).toBe(
    "Home assessments · Grade 2 · 24-Oct-2026",
  );
  // one child's alone says whose, by roll number and never a name
  expect(
    builtName({
      ...facts,
      skills: ["x"],
      kind: "custom",
      kinds: { custom: "Chosen paper" },
      classWords: "Grade 3 · 3B",
      roll: "7",
      day: null,
    }),
  ).toBe("x · Chosen paper · Grade 3 · 3B roll 7");
});

test("a name an educator chose wins; a blank one does not", () => {
  expect(nameOf("Term 2 check", "built")).toBe("Term 2 check");
  expect(nameOf("   ", "built")).toBe("built");
  expect(nameOf(undefined, "built")).toBe("built");
});

test("steps run Created, Printed, Uploaded, Read, Checked, Results in; a class assessment has no approval step", () => {
  const { cells, next } = stepCells(cls({ printed: 28 }));
  expect(cells.map((c) => c.step)).toEqual(["made", "printed", "uploaded", "read", "checked", "signedOff"]);
  expect(cells.map((c) => c.state)).toEqual(["done", "done", "next", "notYet", "notYet", "notYet"]);
  expect(next).toBe("uploaded");
  expect(actionOf(cls({ printed: 28 }), 0)).toEqual({ kind: "upload", label: "Upload" });
});

test("a class assessment made but not printed asks to print; no approval is asked", () => {
  expect(actionOf(cls({ made: 28 }), 0).label).toBe("Print");
  expect(stepCells(cls({ made: 28 })).cells[0].state).toBe("done");
});

test("a home assessment has Approved after Created, with one Approve", () => {
  const home: Counts = { by: by({ made: 12 }), unread: 0, home: true };
  const { cells, next } = stepCells(home);
  expect(cells.map((c) => c.step).slice(0, 3)).toEqual(["made", "approve", "printed"]);
  expect(cells[0].state).toBe("done");
  expect(cells[1].state).toBe("next");
  expect(next).toBe("approve");
  expect(actionOf(home, 0)).toEqual({ kind: "approve", label: "Approve" });
  // once approved the pack is printed, and the next step is the upload
  expect(actionOf({ ...home, by: by({ printed: 12 }) }, 0).kind).toBe("upload");
});

test("partly through a step says how many; answers waiting are red and counted in the action", () => {
  const c = cls({ scanned: 4, checked: 3, "signed off": 3 });
  const checked = stepCells(c, 12).cells.find((x) => x.step === "checked")!;
  expect(checked).toMatchObject({ state: "toCheck", note: "6 of 10" });
  expect(actionOf(c, 12).label).toBe("Check 12 answers");
  expect(actionOf(cls({ scanned: 1 }), 1).label).toBe("Check 1 answer");
});

test("papers read but not yet signed off ask to be signed off; all signed off says See results", () => {
  expect(actionOf(cls({ checked: 10 }), 0).label).toBe("Sign off 10 papers");
  expect(actionOf(cls({ "signed off": 10 }), 0)).toEqual({ kind: "results", label: "See results" });
  expect(stepCells(cls({ "signed off": 10 })).cells.every((c) => c.state === "done")).toBe(true);
});

test("an uploaded file with no answers found yet is Uploaded but not Read", () => {
  const c = cls({ scanned: 5 }, 5);
  const [, , uploaded, read] = stepCells(c).cells;
  expect(uploaded.state).toBe("done");
  expect(read.state).toBe("waiting");
  expect(actionOf(c, 0).kind).toBe("reading");
});

test("furthest step and what is next are said", () => {
  expect(standingWords(cls({ printed: 3 }))).toBe("Printed · next: Uploaded");
  expect(standingWords(cls({ "signed off": 3 }))).toBe("Results in · all done");
});

test("what waits on a person now comes before what waits on paper to come back", () => {
  // two papers still out, one in with an answer to check: check first; once settled, sign off; then the missing papers
  const mixed = cls({ printed: 2, scanned: 1 }, 0);
  expect(actionOf(mixed, 1).kind).toBe("check");
  expect(stepCells(mixed, 1).next).toBe("checked");
  expect(actionOf(cls({ printed: 2, checked: 1 }), 0).kind).toBe("signoff");
  expect(actionOf(cls({ printed: 2, "signed off": 1 }), 0).kind).toBe("upload");
  // a home assessment is approved before anything else is asked of it
  expect(actionOf({ by: by({ made: 3, scanned: 1 }), unread: 0, home: true }, 2).kind).toBe("approve");
});

test("an assessment whose copies are all replaced has nothing to do", () => {
  expect(actionOf(cls({}), 0).kind).toBe("none");
  expect(stepCells(cls({})).next).toBeNull();
});

test("a file is listed against the assessment its codes belong to; one tied to none is not matched", () => {
  const owner = new Map([
    ["CS000001", "assessment~G1A~2026-W43~EQ"],
    ["CS000002", "assessment~G1A~2026-W43~EQ"],
    ["CS000009", "focus~G1A~2026-W43~"],
  ]);
  const known = new Set([...owner.keys(), "CS000777"]);
  const r = matchFiles(
    [
      { file: "IMG_0042.pdf", codes: ["CS000001", "CS000002"] },
      { file: "both.pdf", codes: ["CS000002", "CS000009"] },
      { file: "stranger.pdf", codes: ["CSABCDEF"] },
      { file: "nocode.pdf", codes: [] },
      { file: "spare.pdf", codes: ["CS000777"] },
    ],
    owner,
    known,
  );
  expect(r.byKey.get("assessment~G1A~2026-W43~EQ")).toEqual(["IMG_0042.pdf", "both.pdf"]);
  expect(r.byKey.get("focus~G1A~2026-W43~")).toEqual(["both.pdf"]);
  expect(r.unmatched).toEqual(["stranger.pdf", "nocode.pdf"]);
});

test("a stage can be chosen in the database: the signature reads the same facts as the next step", () => {
  for (const kind of ["approve", "print", "upload", "reading", "check", "signoff", "results", "none"] as const)
    for (const sig of sigsFor(kind)) expect(actionOfSig(sig)).toBe(kind);
  const c = cls({ printed: 2, scanned: 1 });
  expect(sigsFor(actionOf(c, 1).kind)).toContain(sigOf(c, 1));
  expect(sigOf({ by: by({ made: 3 }), unread: 0, home: true }, 0)).toBe("10000001");
});
