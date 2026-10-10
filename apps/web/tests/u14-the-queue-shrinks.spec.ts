/**
 * NY2 — the queue shrinks, and a person sees whether it does (goals/ny2-the-queue-shrinks.yaml). Nimish, 2026-10-10:
 * "The system keeps learning from the number of data points that we keep validating, and the number of data points that
 * we then need to validate becomes lower." Today shows the answers read week by week — settled by the engine alone,
 * checked by a person, still waiting — and how near the reader is to trust; Marking shows how many more right checks
 * each kind of question needs, the database's one rule (`kind_trust`). A paper of the test's own, read this week.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { isoWeek } from "../lib/week";
import { aClass, aReadPaper, aWorksheet } from "./rows";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

const HELD = "read as a right answer; a person checks every answer of this kind until the reader is trusted on it (0 of the last 0 right)";

test.beforeAll(async () => {
  const kids = await aClass(sql, "U14-TEST", "G2", ["Esha"]);
  const sums = ["46 + 38", "57 + 28", "68 + 27"];
  const w = await aWorksheet(sql, {
    code: "U14-A", title: "U14 paper", date: "2026-10-10", band: "G2", week: "U14-TEST",
    items: sums.map((expr, i) => ({ n: i + 1, page: 1, expr, question: expr })),
  });
  await aReadPaper(sql, {
    qr: "U14TEST-1", child: kids.Esha, template: w.template, items: w.items,
    reads: [
      { status: "correct", read: "84" }, // settled by the engine alone
      { status: "correct", read: "85", checkedBy: "e2e@cornerstone.test" }, // checked by a person
      { status: "needs_teacher", read: "95", why: HELD }, // still waiting, for its kind's trust
    ],
  });
});

test("Today shows, week by week, how many answers needed a person", async ({ page }) => {
  const week = isoWeek();
  const [want] = await sql<{ read: number; alone: number; person: number; waiting: number }[]>`
    select count(*)::int as read,
           count(*) filter (where s.standing = 'engine')::int as alone,
           count(*) filter (where s.standing = 'person')::int as person,
           count(*) filter (where s.standing = 'waiting')::int as waiting
    from answer_standing s join item_result r on r.id = s.item_result_id join capture c on c.id = r.capture_id
    where to_char(c.created_at, 'IYYY-"W"IW') = ${week}`;
  expect(want.read, "the test's own paper was read this week").toBeGreaterThanOrEqual(3);
  await page.goto("/today");
  const queue = page.getByRole("region", { name: "Is the queue shrinking?", exact: true });
  const needed = Math.round((100 * (want.person + want.waiting)) / want.read);
  await expect(queue.getByRole("row").filter({ hasText: week }).getByRole("cell")).toHaveText([
    week,
    String(want.read),
    String(want.alone),
    String(want.person),
    String(want.waiting),
    `${needed}%`,
  ]);
  // how near the reader is to trust, as the one rule says
  const kinds = await sql<{ trusted: boolean }[]>`select trusted from kind_trust`;
  await expect(queue).toContainText(`trusted on ${kinds.filter((k) => k.trusted).length} of ${kinds.length}`);
});

test("each kind of question says how many more checks before the reader is trusted on it", async ({ page }) => {
  // every kind Marking lists, in its order: the one rule's number, or the whole window where the reader has stood
  // behind no reading of it yet
  const want = await sql<{ k: number }[]>`
    select coalesce(t.checks_to_trust, (select value::int from threshold where key = 'marking.agreement_window')) as k
    from (select distinct fmt from answer_checked where not never_read) a
    left join kind_trust t on t.tenant_id = (select id from tenant limit 1) and t.fmt = a.fmt
    order by a.fmt`;
  expect(want.length, "the test's paper has checked answers").toBeGreaterThan(0);
  await page.goto("/capture");
  const panel = page.getByRole("region", { name: "How the reader is doing" });
  await panel.getByRole("group", { name: "Show the reader" }).getByRole("button", { name: "By kind of question" }).click();
  const table = panel.getByRole("table", { name: "How the reader is doing" });
  await expect(table.locator("thead th").last()).toHaveText("Checks to trust");
  await expect(table.locator("tbody tr td:last-child")).toHaveText(want.map(({ k }) => (k === 0 ? "trusted" : `${k} more`)));
});
