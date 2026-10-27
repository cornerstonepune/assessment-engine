/**
 * U70 — the rules of a note from staff, before it becomes a GitHub issue (goals/feed_report_from_the_tool.yaml). No
 * browser, no database and no GitHub: what is refused, what is neutralised, and every line the issue holds.
 */
import { expect, test } from "@playwright/test";
import {
  browserOf,
  issueBody,
  issueTitle,
  neutralise,
  REFUSED_WORDS,
  refusal,
  routeOnly,
  seenAs,
  TITLE_MAX,
  type Note,
} from "../lib/feedback-words";
import { createIssue, githubConnected, toolIssues } from "../lib/github";

const CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";

const NOTE: Note = {
  kind: "bug",
  doing: "Printing the Grade 3 papers",
  happened: "I expected a PDF.\nNothing came out.",
  howOften: "every time",
  route: "/growth/3f2a9c1e-0000-4000-8000-000000000000?tab=maths",
  role: "educator",
  classes: "3A",
  browser: browserOf(CHROME),
  at: new Date("2026-10-27T08:35:00Z"),
};

test("a phone number or an email in the note is refused with a kind message", () => {
  for (const bad of ["call 9876543210", "+91 98765 43210", "(020) 2567-8901 ext", "mother is asha.k@gmail.com"]) {
    expect(refusal("fine words", bad), bad).toBe(REFUSED_WORDS);
  }
  expect(REFUSED_WORDS).toBe("That looks like a name or a phone number; please take it out");
  for (const fine of ["roll number 12 of 3A", "page 2, question 14", "27-10-2026 at 9:30", "45 + 38 = 83"]) {
    expect(refusal(fine), fine).toBeNull();
  }
});

test("an @mention or #number in the note cannot ping anyone or link an issue", () => {
  const body = issueBody({ ...NOTE, happened: "ask @nimishshah1989 and @cornerstonepune/team about #12\n~~~\n<b>x</b> https://evil.test" });
  // no @ or # is followed straight by a name or a number anywhere in the issue
  expect(body).not.toMatch(/[@#][\w]/);
  expect(neutralise("@a #1")).toBe("@​a #​1");
  // the words sit in a fence longer than any they hold, so `~~~`, HTML and a link in them are shown as text
  expect(body).toContain("~~~~text\nask @");
  expect(body).toMatch(/~~~~text\n[^]*<b>x<\/b> https:\/\/evil\.test\n~~~~/);
  expect(issueTitle({ ...NOTE, happened: "@everyone look at #3" })).toBe("@​everyone look at #​3");
});

test("the issue says the role and class, the page without its ids, the browser and the time, and nothing else", () => {
  const body = issueBody(NOTE);
  expect(body.split("\n").filter((l) => l.startsWith("### "))).toEqual([
    "### What kind?",
    "### What were you doing?",
    "### What did you expect, and what happened?",
    "### How often?",
    "### Page",
    "### Reported by",
    "### Browser",
    "### When",
  ]);
  expect(body).toContain("Something is broken");
  expect(body).toContain("`/growth/[id]`");
  expect(body).not.toContain("3f2a9c1e");
  expect(body).not.toContain("tab=");
  expect(body).toContain("an educator of 3A");
  expect(body).toContain("Chrome 130 on Windows");
  expect(body).not.toContain("Mozilla");
  expect(body).toContain("27-Oct-2026 14:05 IST");
  expect(issueBody({ ...NOTE, role: "coordinator", classes: "" })).toContain("a coordinator");
  expect(issueBody({ ...NOTE, kind: "feature" })).not.toContain("How often");
  expect(routeOnly("/worksheets/CS0A1B2C/print#top")).toBe("/worksheets/[id]/print");
  expect(routeOnly("https://elsewhere.test/x")).toBe("/");
});

test("the title is the first line of the person's words, at most 80 characters", () => {
  expect(issueTitle(NOTE)).toBe("I expected a PDF.");
  const long = issueTitle({ ...NOTE, happened: "x".repeat(200) });
  expect(long.length).toBeLessThanOrEqual(TITLE_MAX);
  expect(issueTitle({ ...NOTE, happened: "  \n", doing: "Opening Check answers" })).toBe("Opening Check answers");
  // and the person sees what came of it: received, taken up once Nimish adds scope-locked, done once closed
  expect(seenAs(undefined)).toBe("received");
  expect(seenAs({ closed: false, labels: ["from-the-tool"] })).toBe("received");
  expect(seenAs({ closed: false, labels: ["from-the-tool", "scope-locked"] })).toBe("takenUp");
  expect(seenAs({ closed: true, labels: [] })).toBe("done");
});

test("without the token nothing is sent and no secret is said", async () => {
  const had = process.env.GITHUB_FEEDBACK_TOKEN;
  delete process.env.GITHUB_FEEDBACK_TOKEN;
  try {
    expect(githubConnected()).toBe(false);
    expect(await createIssue("t", "b", ["from-the-tool"])).toBe("not connected");
    expect((await toolIssues()).size).toBe(0);
  } finally {
    if (had) process.env.GITHUB_FEEDBACK_TOKEN = had;
  }
});
