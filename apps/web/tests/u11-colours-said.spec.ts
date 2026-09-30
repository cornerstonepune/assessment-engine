/**
 * U11 — the colours said, and a check for grey (goals/u11-colours-said.yaml).
 *
 * Nimish, 2026-09-30: "The clarity of what each of the colors means has not been very clearly mentioned. How do we
 * classify students across different tiers?" and "for areas where we don't have sufficient data points … (which is in
 * gray), we should have a clear recommendation around the next set of assessments".
 *
 * The class is the test's own, three Grade 2 children made once and kept: Asha has 2-digit + 2-digit right six times
 * (green); Bina has it right once (grey: too few answers); Chetan has not answered it, and takes the smaller digit
 * from the larger on 2-digit − 2-digit again and again (red).
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "U11-TEST";

type Answer = [skill: string, rung: string, right: boolean, mistakes: string[]];
const CHILDREN: { roll: string; name: string; answers: Answer[] }[] = [
  { roll: "1", name: "Asha", answers: Array<Answer>(6).fill(["NUM.OPS.01", "R22", true, []]) },
  { roll: "2", name: "Bina", answers: [["NUM.OPS.01", "R22", true, []]] },
  {
    roll: "3",
    name: "Chetan",
    answers: [
      ...Array<Answer>(2).fill(["NUM.OPS.02", "R24", false, ["M_SMALL_FROM_LARGE"]]),
      ["NUM.OPS.02", "R24", false, []],
    ],
  },
];

const ids: Record<string, string> = {};
test.beforeAll(async () => {
  const [{ id: tenant }] = await sql<{ id: string }[]>`select id from tenant limit 1`;
  for (const c of CHILDREN) {
    const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = ${c.roll}`;
    if (had) {
      ids[c.name] = had.id;
      continue;
    }
    const [{ id }] = await sql<{ id: string }[]>`
      insert into child (tenant_id, roll_no, section, band) values (${tenant}, ${c.roll}, ${SECTION}, 'G2') returning id`;
    await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant}, ${id}, ${c.name})`;
    for (const [skill, rung, right, mistakes] of c.answers) {
      await sql`
        insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                    observed_at, confirmed_by)
        values (${tenant}, ${id}, ${skill}, ${rung}, ${right}, ${mistakes}, 'item', now(), 'e2e')`;
    }
    await sql`select rebuild_child_skill_state(${id}::uuid)`;
    ids[c.name] = id;
  }
});
test.afterAll(async () => sql.end());

/** The rows the graph decides a colour by, and the check size the pages derive from them. */
async function rules() {
  const [r] = await sql<{ min_events: number; min_obs: number; promote: number; demote: number; g2: string }[]>`
    select (select value from threshold where key = 'state.min_events')::float as min_events,
           (select value from threshold where key = 'state.min_observers')::float as min_obs,
           (select value from threshold where key = 'next_sheet.promote_at')::float as promote,
           (select value from threshold where key = 'next_sheet.demote_below')::float as demote,
           (select value ->> 'G2' from config where key = 'prescribe.band_default') as g2`;
  return { ...r, check: Math.max(r.min_events, Math.round(1 / (1 - r.promote))) };
}

test("each colour is said in the rule's own numbers, wherever colours show", async ({ page }) => {
  const r = await rules();
  const pc = (x: number) => `${Math.round(x * 100)}%`;
  for (const path of [`/growth/class/${SECTION}`, "/growth", `/growth/${ids.Bina}`]) {
    await page.goto(path);
    const key = page.getByRole("region", { name: "What the colours mean" });
    await expect(key.locator("tbody tr")).toHaveCount(4);
    await expect(key.locator('tr[data-rag="red"]')).toContainText(`The same mistake twice or more, or under ${pc(r.demote)} right.`);
    await expect(key.locator('tr[data-rag="amber"]')).toContainText(`${pc(r.demote)} up to ${pc(r.promote)} right`);
    await expect(key.locator('tr[data-rag="green"]')).toContainText(`${pc(r.promote)} or more right, across ${r.min_obs} papers or more`);
    await expect(key.locator('tr[data-rag="grey"]')).toContainText(`Fewer than ${r.min_events} checked answers`);
    await expect(key.locator('tr[data-rag="grey"]')).toContainText(`A ${r.check}-question check places the child.`);
  }
  // and the grid's own colours are the ones the key says: Asha green, Bina grey, Chetan red
  await page.goto(`/growth/class/${SECTION}`);
  const cell = (who: string, col: string) => page.locator(`tr[data-child="${ids[who]}"] td[data-col="${col}"]`);
  await expect(cell("Asha", "NUM.OPS.01|R22")).toHaveAttribute("data-rag", "green");
  await expect(cell("Bina", "NUM.OPS.01|R22")).toHaveAttribute("data-rag", "grey");
  await expect(cell("Chetan", "NUM.OPS.02|R24")).toHaveAttribute("data-rag", "red");
});

test("a grey or empty skill has the check that would place the child, and one click opens it in the maker", async ({ page }) => {
  const r = await rules();
  await page.goto(`/growth/class/${SECTION}`);
  const checks = page.getByRole("region", { name: "Checks that would place them" });
  // 2-digit + 2-digit: Bina has one answer, Chetan none; Asha is green and is not in it
  const add = checks.locator('tr[data-check="NUM.OPS.01|R22"]');
  await expect(add).toContainText("Bina (1 answer)");
  await expect(add).toContainText("Chetan (none)");
  await expect(add).not.toContainText("Asha");
  await expect(add).toContainText(`${r.check} questions · ${r.g2}`);
  // 2-digit − 2-digit: Chetan is red on it, placed; Asha and Bina have no answers
  const sub = checks.locator('tr[data-check="NUM.OPS.02|R24"]');
  await expect(sub).toContainText("Asha (none)");
  await expect(sub).not.toContainText("Chetan");

  await add.getByRole("link", { name: "Make this check →" }).click();
  await expect(page).toHaveURL(/\/papers\/make\?/);
  const plan = page.getByRole("table", { name: "Each child's paper" });
  await expect(plan.locator("tbody tr")).toHaveCount(2);
  await expect(plan.locator(`tr[data-child="${ids.Bina}"]`)).toContainText(`2-digit + 2-digit · ${r.g2} · ${r.check} questions`);
  await expect(plan.locator(`tr[data-child="${ids.Chetan}"]`)).toContainText(`2-digit + 2-digit · ${r.g2} · ${r.check} questions`);
  await expect(page.getByRole("radio", { name: /Class assessment/ })).toBeChecked();
  await expect(page.getByRole("button", { name: "Make and approve 2 papers" })).toBeEnabled();

  // a child's own page: the same check, for them alone
  await page.goto(`/growth/${ids.Bina}`);
  const hers = page.getByRole("region", { name: "Checks that would place Bina" });
  await expect(hers.locator('tr[data-check="ADD.2D2D"]')).toContainText("1 answer so far");
  const href = await hers.locator('tr[data-check="ADD.2D2D"]').getByRole("link").getAttribute("href");
  const q = new URL(href!, "http://x").searchParams;
  expect([q.getAll("c"), q.get("a"), q.get("kind"), q.get("way")]).toEqual([[ids.Bina], `ADD.2D2D~${r.g2}~${r.check}`, "assessment", "each"]);
});
