// What the K2 educator's screen specs share (task M1-09): the timetable's switch, the screenshots every screen is shot
// at (1280 and 390 px, and 1280 at 200% zoom), and the rule that every tap is at least 44 px each way at both widths.
import { execFileSync } from "node:child_process";
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

/** Fortnight 10 as the school wrote it, into the tests' placeholder K2 class, by M1-06's own command as a person runs
 * it (`engine timetable load`). Safe to run twice. */
export function loadFortnight10(section: string) {
  const tab = (f: string) => path.resolve(__dirname, "../../../supabase/seed/k2_tabs_2026_11_04", f);
  execFileSync(path.resolve(__dirname, "../../../bin/engine"), ["timetable", "load", "--frame", tab("frame.csv"), "--planner", tab("planner.csv"), "--calendar", tab("calendar.csv"), "--spans", tab("frame_spans.json"), "--section", section, "--grade", "K2", "--from", "10", "--to", "10", "--year", "2031-32", "--apply"], { env: process.env, stdio: "pipe" });
}

/** A few catalogue items of the tests' own, tied to Fortnight 10's real activities (tulips, the dustbin, beads), so a
 * list built from the plan has lines: one the school keeps, one the class keeps, one not tracked with no quantity. */
export async function materialsFor(sql: Sql) {
  const [{ id: t }] = await sql<{ id: string }[]>`select id from tenant order by created_at limit 1`;
  const items = [
    ["MAT-M109-1", "Craft paper", "sheet", "school", 5, "ACT-K2-0133", 2],
    ["MAT-M109-2", "Dustbin", "piece", "class", 300, "ACT-K2-0287", 1],
    ["MAT-M109-3", "Beads", "packet", null, null, "ACT-K2-0246", null],
  ] as const;
  for (const [code, name, unit, home, value, activity, qty] of items) {
    await sql`insert into material_item (tenant_id, code, name, unit, home, unit_value) values (${t}, ${code}, ${name}, ${unit}, ${home}, ${value})
      on conflict (tenant_id, code) do nothing`;
    await sql`insert into activity_material (tenant_id, activity_code, material_code, quantity, ord) values (${t}, ${activity}, ${code}, ${qty}, 1)
      on conflict do nothing`;
  }
  await sql`insert into material_item (tenant_id, code, name, unit) values (${t}, 'MAT-M109-4', 'Glue stick', 'piece') on conflict (tenant_id, code) do nothing`;
}
