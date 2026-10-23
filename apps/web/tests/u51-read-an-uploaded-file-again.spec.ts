/**
 * U51 — a file sent to the engine can be read again from Marking (goals/ck2-photograph-is-its-page.yaml). Nimish,
 * 2026-10-22: the 22 Oct file is read again with the fix; today the only route takes a Drive link. A finished scan lists a
 * "Read again" button; the engine answers in words when it cannot (here: it no longer keeps the file), and the page says
 * what it said. The reading itself, and what it supersedes, are the engine's tests (`tests/test_photograph_page.py`).
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const FILE = `U51 scan ${Date.now()}.pdf`;

test.beforeAll(async () => {
  const [t] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  await sql`insert into flow_run (tenant_id, flow, trigger, status, finished_at, result)
    values (${t.id}, 'read-scan', ${`e2e@cornerstone.test: ${FILE}`}, 'ok', now(), ${sql.json({ pages: 2, file: FILE, copies: [] })})`;
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;
  await sql.end();
});

test("a finished scan can be read again, and the page says why when the engine will not", async ({ page }) => {
  await page.goto("/capture");
  const run = page.getByRole("table", { name: "Scans read last" }).getByRole("row").filter({ hasText: FILE }).first();
  await run.getByRole("button", { name: "Read again" }).click();
  await expect(page).toHaveURL(/read=refused/);
  await expect(page.getByRole("region", { name: "Read a scan" })).toContainText("is no longer kept by the engine: send the scan again");
});
