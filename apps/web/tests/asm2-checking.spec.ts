/**
 * Check answers by assessment (goals/asm2_by_topic_and_checking.yaml), at 1440 px. Nimish, 26 Oct 2026: "When I come to
 * needs checking, everyone checks the assessment by the last upload that they do. Think about how you really make these
 * pages useful."
 *
 * Two assessments of a class of the test's own: Alpha (two children's papers, 3 answers waiting, in five days ago) and Beta
 * (one paper, a wrong and a blank held for a person, in yesterday); no answer the engine was sure of, so no spot-check. The queue runs Alpha to its end before Beta begins.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aClass, aReadPaper, aWorksheet } from "./rows";

test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "ASM2-CHK";
const HELD = {
  wrong: "read as a wrong answer; a person checks every wrong answer before it counts",
  blank: "read as blank; a person checks every blank before it counts",
};
let alpha: { asha: string[]; bina: string[] };
let beta: string[];

test.beforeAll(async () => {
  const kids = await aClass(sql, SECTION, "G2", ["Asha", "Bina", "Chetan"]);
  const sums = ["46 + 38", "57 + 28", "68 + 27"];
  const sheet = (code: string, title: string) =>
    aWorksheet(sql, {
      code,
      title,
      date: "2026-10-20",
      band: "G2",
      week: `${code}-WEEK`,
      items: sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
    });
  const [a, b] = [await sheet("ASM2-A", "ASM2 Alpha"), await sheet("ASM2-B", "ASM2 Beta")];
  const wait = (read: string) => ({ status: "needs_teacher", read, why: "the reader was not sure", guess: read });
  const asha = await aReadPaper(sql, { qr: "CSB2C001", child: kids.Asha, template: a.template, items: a.items, reads: [wait("84"), wait("85")] });
  const bina = await aReadPaper(sql, { qr: "CSB2C002", child: kids.Bina, template: a.template, items: a.items, reads: [wait("84")] });
  const chetan = await aReadPaper(sql, {
    qr: "CSB2C003",
    child: kids.Chetan,
    template: b.template,
    items: b.items,
    reads: [
      { status: "needs_teacher", read: "73", why: HELD.wrong, guess: "73" },
      { status: "needs_teacher", why: HELD.blank },
    ],
  });
  alpha = { asha: asha.results, bina: bina.results };
  beta = chetan.results;
  await sql`update capture set created_at = now() - interval '5 days' where id in (${asha.capture}, ${bina.capture})`;
  await sql`update capture set created_at = now() - interval '1 day' where id = ${chetan.capture}`;
});
test.afterAll(async () => sql.end());

const lines = (page: Page) => page.locator("tr[data-assessment]");

test("Check answers lists one line per assessment, with its papers waiting, its answers left and its oldest wait", async ({ page }) => {
  await page.goto(`/capture/check?class=${SECTION}`);
  const table = page.getByRole("table", { name: "Left to check, by assessment" });
  await expect(table.locator("thead th")).toContainText(["Assessment", "Papers waiting", "Answers left", "Oldest wait"]);
  await expect(lines(page)).toHaveCount(2);
  // the one that has waited longest first
  const [one, two] = [lines(page).nth(0), lines(page).nth(1)];
  await expect(one).toContainText("ASM2 Alpha");
  await expect(one.locator("td[data-label='Papers waiting']")).toHaveText("2");
  await expect(one.locator("td[data-label='Answers left']")).toHaveText("3");
  await expect(one.locator("td[data-label='Oldest wait']")).toHaveText("5 days");
  await expect(one).toContainText(SECTION);
  await expect(two).toContainText("ASM2 Beta");
  await expect(two.locator("td[data-label='Papers waiting']")).toHaveText("1");
  await expect(two.locator("td[data-label='Answers left']")).toHaveText("2");
  await expect(two.locator("td[data-label='Oldest wait']")).toHaveText("1 day");
  await expect(one.locator("[data-action=check-assessment]")).toBeVisible();
});

test("an assessment opens into its papers, and finishing a paper offers the next paper of the same assessment", async ({ page }) => {
  await page.goto(`/capture/check?id=${alpha.asha[0]}`);
  // the assessment on the card is open: its papers, in roll order, with the child, the code and the answers left
  const papers = page.getByRole("table", { name: /^Papers of ASM2 Alpha/ });
  await expect(papers.getByRole("row", { name: /^1 Asha CSB2C001 2 / })).toBeVisible();
  await expect(papers.getByRole("row", { name: /^2 Bina CSB2C002 1 / })).toBeVisible();
  // another assessment is opened from its line without leaving the answer on the card
  await page.goto(`/capture/check?id=${alpha.asha[0]}&class=${SECTION}`);
  await lines(page)
    .nth(1)
    .getByRole("link", { name: /ASM2 Beta/ })
    .click();
  await expect(page.getByRole("table", { name: /^Papers of ASM2 Beta/ }).getByRole("row", { name: /CSB2C003/ })).toBeVisible();
  await expect(page.getByText("Asha · paper CSB2C001")).toBeVisible();
  // Asha's last answer: her paper is done, and the next paper is Bina's, of the same assessment
  await page.goto(`/capture/check?id=${alpha.asha[1]}`);
  await expect(page.getByText("answer 2 of 2 · 0 left")).toBeVisible();
  await expect(page.locator("[data-ux=next]")).toHaveText(/^Next paper in this assessment/);
  await page.locator("[data-ux=next]").click();
  await expect(page.getByText("Bina · paper CSB2C002")).toBeVisible();
  // Bina's is the last of Alpha: the next is another assessment, said so
  await expect(page.locator("[data-ux=next]")).toHaveText(/^This assessment is done — next assessment/);
});

test("the three signals stay three on the card, and the flat list of every answer is gone", async ({ page }) => {
  // no flat table of answers, and no page of them
  await page.goto(`/capture/check?class=${SECTION}`);
  await expect(page.getByRole("table", { name: "Left to check", exact: true })).toHaveCount(0);
  await expect(page.getByRole("table", { name: "Children in this file" })).toHaveCount(0);
  await expect(page.locator("tbody tr").filter({ hasText: /^\d+\s+ASM2-CHK/ })).toHaveCount(0);
  // wrong, blank and wrong-with-working are said apart on the card, as before
  await page.goto(`/capture/check?id=${beta[0]}`);
  await expect(page.getByText("The engine read this as a wrong answer.")).toBeVisible();
  await page.goto(`/capture/check?id=${beta[1]}`);
  await expect(page.getByText("The engine found nothing written here.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Nothing is written here" })).toBeVisible();
});
