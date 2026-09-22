/**
 * How it works (goals/workflows-visible.yaml).
 *
 * Nimish, 2026-09-22: "shows each of the steps as a proper workflow, what is working, and how things are
 * connected." The page draws `workflows.json` — the map the engine's code is held to — so the checks here
 * read that same file and hold the page to it: every step in its workflow, its live number from the
 * database, and the steps each one hands on to.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import postgres from "postgres";

type Step = { code: string; workflow: string; name: string; built: string; takes: string[]; gives: string[]; files: string[] };
const MAP = JSON.parse(readFileSync(path.join(__dirname, "..", "..", "..", "workflows.json"), "utf8")) as {
  workflows: { code: string; name: string }[];
  steps: Step[];
  handovers: { from: string; to: string }[];
};
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
test.afterAll(async () => sql.end());

test("every step of the map is drawn in its workflow, with what it is doing now and where it hands on", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "How it works" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("How it works");
  for (const w of MAP.workflows) {
    const section = page.getByRole("region", { name: `${w.code} · ${w.name}` });
    await expect(section).toBeVisible();
    for (const s of MAP.steps.filter((x) => x.workflow === w.code)) {
      const card = section.getByRole("article", { name: s.name });
      await expect(card, s.code).toBeVisible();
      await expect(card.getByText(s.built === "live" ? "working" : s.built === "partly" ? "partly built" : "not built yet")).toBeVisible();
      // where this step's output goes: every step that takes something it gives
      for (const next of MAP.steps.filter((x) => x.code !== s.code && x.takes.some((t) => s.gives.includes(t)))) {
        await expect(card.getByRole("link", { name: `${next.code} ${next.name}` }), `${s.code} hands on to ${next.code}`).toBeVisible();
      }
      if (s.files.length) {
        await card.getByText("Files, commands and screens").click();
        await expect(card.getByText(`packages/engine/${s.files[0]}`)).toBeVisible();
      }
    }
  }
  for (const h of MAP.handovers) await expect(page.getByText(h.from).first()).toBeVisible();
});

test("a step's number is the database's own, read now", async ({ page }) => {
  const [n] = await sql<{ items: number; worksheets: number }[]>`
    select (select count(*) from item where status = 'active')::int as items,
           (select count(*) from sheet_template where source = 'library' and retired_at is null)::int as worksheets`;
  await page.goto("/workflows");
  await expect(page.locator('[data-measure="N2"]')).toContainText(n.items.toLocaleString("en-IN"));
  await expect(page.locator('[data-measure="N6"]')).toContainText(n.worksheets.toLocaleString("en-IN"));
  // a step the map says is not built has no number: nothing is invented for it
  for (const s of MAP.steps.filter((x) => x.built === "not built")) await expect(page.locator(`[data-measure="${s.code}"]`)).toHaveCount(0);
});

test("the map fits a phone", async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 860 });
  await page.goto("/workflows", { waitUntil: "networkidle" });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
