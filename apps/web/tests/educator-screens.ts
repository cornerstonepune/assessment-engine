// What the K2 educator's screen specs share (task M1-09): the timetable's switch, the screenshots every screen is shot
// at (1280 and 390 px, and 1280 at 200% zoom), and the rule that every tap is at least 44 px each way at both widths.
import path from "node:path";
import { mkdirSync } from "node:fs";
import { expect, type Page } from "@playwright/test";
import type { Sql } from "postgres";

export const SHOTS = path.resolve(__dirname, "../../../docs/screens/m1-09-built");

/** `educator.timetable_enabled` on or off (M1-06's row; a test's own value). */
export const timetableSwitch = (sql: Sql, on: boolean) => sql`
  insert into config (tenant_id, key, value, description) select id, 'educator.timetable_enabled', ${on ? sql`'true'::jsonb` : sql`'false'::jsonb`}, 'm1-09 test' from tenant
  on conflict (tenant_id, key) do update set value = excluded.value`;

export async function shoot(page: Page, name: string) {
  mkdirSync(SHOTS, { recursive: true });
  for (const [size, w, zoom] of [["1280", 1280, 1], ["390", 390, 1], ["1280-200pct", 640, 2]] as const) {
    await page.setViewportSize({ width: w, height: 900 });
    await page.evaluate((z) => ((document.body.style as unknown as { zoom: string }).zoom = String(z)), zoom);
    await page.screenshot({ path: path.join(SHOTS, `${name}-${size}.png`), fullPage: true });
  }
  await page.evaluate(() => ((document.body.style as unknown as { zoom: string }).zoom = "1"));
  await page.setViewportSize({ width: 1280, height: 900 });
}

/** Every link and button under `scope` is at least 44 px high and wide, on a desktop and on a phone. */
export async function tapsAreBig(page: Page, scope = "[data-educator]") {
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const small = await page.locator(`${scope} a:visible, ${scope} button:visible`).evaluateAll((els) =>
      els
        .map((e) => [e.textContent?.trim(), Math.round(e.getBoundingClientRect().height), Math.round(e.getBoundingClientRect().width)] as const)
        .filter(([, h, w]) => h < 44 || w < 44),
    );
    expect(small, `at ${width} px`).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}

/** D-073 R3: the display face (Cormorant Garamond, a thin face) only at 24 px and above. */
export async function displayFaceOnlyLarge(page: Page) {
  const small = await page.locator("[data-educator] *").evaluateAll((els) =>
    els
      .filter((e) => e.childNodes.length && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()))
      .map((e) => [e.textContent?.trim().slice(0, 30), getComputedStyle(e).fontFamily, parseFloat(getComputedStyle(e).fontSize)] as const)
      .filter(([, f, px]) => /Cormorant/.test(f) && px < 24),
  );
  expect(small).toEqual([]);
}
