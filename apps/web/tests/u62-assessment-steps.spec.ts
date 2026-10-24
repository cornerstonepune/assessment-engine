/**
 * The Assessments page's logic (goals/asm_assessments_page.yaml): a name built from the sheet's own code, the steps an
 * assessment has been through and the one thing to do next, and a file listed against its assessment. No page is opened.
 */
import { expect, test } from "@playwright/test";
import { actionOf, builtName, matchFiles, nameOf, stepCells, standingWords, type Counts } from "../lib/assessment-steps";

const KINDS = { assessment: "Class assessment", focus: "Home assessment" };
const by = (o: Partial<Counts["by"]>): Counts["by"] => ({ made: 0, printed: 0, scanned: 0, checked: 0, "signed off": 0, ...o });
const cls = (o: Partial<Counts["by"]>, unread = 0): Counts => ({ by: by(o), unread, home: false });

test("a name is built from the sheet's skill, class, kind and day, never a file name; a day is said as every page says it", () => {
  expect(builtName({ title: "Equal groups (repeated addition) · Easy", kind: "assessment", kinds: KINDS, classWords: "Grade 1", day: "2026-10-19" })).toBe(
    "Equal groups (repeated addition) · Easy · Grade 1 · class assessment · 19-Oct-2026",
  );
  // a part the sheet does not carry is left out, and a title that already says its kind is not made to say it twice
  expect(builtName({ title: "Home assessments", kind: "focus", kinds: KINDS, classWords: null, day: null })).toBe("Home assessments");
  expect(builtName({ title: "Home assessments", kind: "focus", kinds: KINDS, classWords: "Grade 2", day: "2026-10-24" })).toBe("Home assessments · Grade 2 · 24-Oct-2026");
});

test("a name an educator chose wins; a blank one does not", () => {
  expect(nameOf("Term 2 check", "built")).toBe("Term 2 check");
  expect(nameOf("   ", "built")).toBe("built");
  expect(nameOf(undefined, "built")).toBe("built");
});

test("steps run Made, Printed, Uploaded, Read, Checked, Signed off; a class assessment has no approval step", () => {
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

test("a home assessment starts at To approve, with one Approve", () => {
  const home: Counts = { by: by({ made: 12 }), unread: 0, home: true };
  const { cells, next } = stepCells(home);
  expect(cells[0].step).toBe("approve");
  expect(cells[0].state).toBe("next");
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
  expect(standingWords(cls({ printed: 3 }))).toBe("Printed / given · next: Uploaded");
  expect(standingWords(cls({ "signed off": 3 }))).toBe("Signed off · all done");
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
  const owner = new Map([["CS000001", "assessment~G1A~2026-W43~EQ"], ["CS000002", "assessment~G1A~2026-W43~EQ"], ["CS000009", "focus~G1A~2026-W43~"]]);
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
