/**
 * U64 — a file read again is one line on Marking, its attempts inside it (goals/dbt_one_read_per_file.yaml). Nimish,
 * 2026-10-26: one 23-page file, "Read again" pressed several times, five identical "reading stopped" lines for it. The
 * line shows the reading that stands — the one going on, else the one that finished — and, while one is going on, no
 * "Read again" anywhere for that file: the engine refuses a second reading of it (`tests/test_one_read_per_file.py`).
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const FILE = `U64 scan ${Date.now()}.pdf`;
const STOPPED = 'QueryCanceled: canceling statement due to statement timeout CONTEXT: while inserting index tuple (14,44) in relation "sheet_instance"';

async function run(status: "ok" | "error" | "running", minutesAgo: number) {
  const [t] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  await sql`insert into flow_run (tenant_id, flow, trigger, status, error, started_at, finished_at, result)
    values (${t.id}, 'read-scan', ${`e2e@cornerstone.test: ${FILE}`}, ${status}, ${status === "error" ? STOPPED : null},
            now() - ${`${minutesAgo} minutes`}::interval, ${status === "running" ? null : sql`now()`},
            ${sql.json({ pages: 23, file: FILE, copies: [] })})`;
}

test.describe.configure({ mode: "serial" }); // the second adds a reading the first must not see

test.beforeAll(async () => {
  await run("ok", 30); // the one reading that finished
  for (const m of [3, 2, 1]) await run("error", m); // the presses after it, each stopped
});
test.afterAll(async () => {
  await sql`delete from flow_run where flow = 'read-scan' and trigger like ${`%${FILE}`}`;
  await sql.end();
});

const rowsOf = (page: import("@playwright/test").Page) =>
  page.getByRole("table", { name: "Scans read last" }).getByRole("row").filter({ hasText: FILE });

test("a file read four times is one line, the finished reading on it and the stopped ones inside", async ({ page }) => {
  await page.goto("/capture");
  await expect(rowsOf(page)).toHaveCount(1);
  await expect(rowsOf(page).first()).not.toContainText("reading stopped");
  const other = page.getByRole("list", { name: `Other readings of ${FILE}` });
  await page.getByText("Read 4 times; the other 3 readings").click();
  await expect(other.getByRole("listitem")).toHaveCount(3);
  await expect(other).toContainText("stopped: QueryCanceled");
});

test("while the file is being read, it offers no Read again", async ({ page }) => {
  await run("running", 0);
  await page.goto("/capture");
  await expect(rowsOf(page)).toHaveCount(1);
  await expect(rowsOf(page).first()).toContainText("reading now");
  await expect(rowsOf(page).first().getByRole("button", { name: "Read again" })).toHaveCount(0);
});
