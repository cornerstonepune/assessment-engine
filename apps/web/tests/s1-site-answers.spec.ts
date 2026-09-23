/**
 * Step 1 — the site answers (goals/s1-site-answers.yaml).
 *
 * The live Question bank hung for Vercel's full five minutes on every click, a click showed nothing
 * at all, and an outage in the staff check sent a signed-in founder to the login page. These tests
 * stage the outage for real — a transaction on the local copy holds a lock on a table the page reads
 * — and hold the website to answering in words within 12 seconds.
 */
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

/** Hold an exclusive lock on `table` for as long as `work` runs, then let it go. */
async function whileLocked(table: "item" | "config", work: () => Promise<void>): Promise<void> {
  const tx = await sql.reserve();
  try {
    await tx`begin`;
    await tx.unsafe(`lock table ${table} in access exclusive mode`);
    await work();
  } finally {
    await tx`rollback`;
    tx.release();
  }
}

const COULD_NOT_LOAD = "This page could not load";

async function menu(page: Page, label: string) {
  await page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: label, exact: true }).click();
}

test("a click shows the page is loading at once, and a database that does not answer is said in words within 12 s", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  await whileLocked("item", async () => {
    const clicked = Date.now();
    await menu(page, "Question bank");
    await expect(page.getByRole("status", { name: "Loading this page" })).toBeVisible({ timeout: 1_500 });
    await expect(page.getByRole("heading", { name: COULD_NOT_LOAD })).toBeVisible({ timeout: 12_000 });
    expect(Date.now() - clicked).toBeLessThan(12_000);
    await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  });
  // Once the database answers again, Try again brings the page back.
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Question bank" })).toBeVisible({ timeout: 10_000 });
});

test("when the staff check cannot reach the database, the page says so instead of asking you to sign in again", async ({ page }) => {
  await whileLocked("config", async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: COULD_NOT_LOAD })).toBeVisible({ timeout: 12_000 });
    await expect(page).not.toHaveURL(/\/login/);
  });
});

// Before this, one opening of the Skill Map pre-loaded every page behind its 85 table links at once.
// Now only the menu pages are fetched ahead — Next 16 asks for a page's outline and its loading
// screen separately, so at most two small requests each.
test("opening the Skill Map loads nothing ahead but the menu pages", async ({ page }) => {
  const MENU = ["/today", "/", "/worksheets", "/library", "/capture", "/capture/check", "/growth", "/home", "/workflows"];
  const background: string[] = [];
  page.on("request", (r) => {
    if (r.resourceType() !== "document" && r.headers()["rsc"] === "1") background.push(new URL(r.url()).pathname);
  });
  await page.goto("/", { waitUntil: "networkidle" });
  await page.waitForTimeout(2_000);
  expect(background.filter((p) => !MENU.includes(p)), "pre-loaded a page that is not on the menu").toEqual([]);
  expect(background.length).toBeLessThanOrEqual(2 * MENU.length);
});

test("every menu page opens within three seconds of its click", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  for (const [label, heading] of [
    ["Today", "Today"],
    ["Children", "Children"],
    ["Marking", "Capture & Mark"],
    ["Papers", "Worksheets"],
    ["Question bank", "Question bank"],
    ["Curriculum", "Skill Map"],
  ]) {
    const clicked = Date.now();
    await menu(page, label);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible({ timeout: 10_000 });
    expect(Date.now() - clicked, `${label} took too long`).toBeLessThan(3_000);
  }
});
