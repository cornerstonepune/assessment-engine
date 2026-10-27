/**
 * Before anything prints, an educator sees the paper (goals/preview-before-print.yaml). Nimish, 2026-10-21: "a teacher
 * can only see the assessment when they print. They click on print just to see the assessment".
 *
 * Every place a paper is made shows its questions under their skill and level, offers "Different questions", which
 * makes nothing, and prints exactly the questions last shown. That a preview writes nothing and a print is the draw
 * shown is the engine's own test (tests/test_seen.py); this is what an educator sees and does, page by page.
 *
 * The child is the test's own, made once on the copy with checked answers and kept (evidence is append-only); the
 * papers the test makes are removed.
 */
import { expect, test, type Locator, type Page } from "@playwright/test";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const SECTION = "P4-TEST-C";
const ASK = "SUB.3D3D~Easy~4";
const SHOTS = "test-results/preview-before-print";

async function testChild(): Promise<string> {
  const [had] = await sql<{ id: string }[]>`select id from child where section = ${SECTION} and roll_no = '1'`;
  if (had) return had.id;
  const [{ tenant_id }] = await sql<{ tenant_id: string }[]>`select id as tenant_id from tenant limit 1`;
  const [{ id }] = await sql<{ id: string }[]>`
    insert into child (tenant_id, roll_no, section, band) values (${tenant_id}, '1', ${SECTION}, 'G3') returning id`;
  await sql`insert into pii.child (tenant_id, child_id, first_name) values (${tenant_id}, ${id}, 'Preview')`;
  // 3-digit − 3-digit: 2 of 8, taking the smaller digit from the larger four times — the home assessment's one skill
  const answers: [string, string, boolean, string[]][] = [
    ...Array(4).fill(["NUM.OPS.02", "R31", false, ["M_SMALL_FROM_LARGE"]]),
    ...Array(2).fill(["NUM.OPS.02", "R31", false, []]),
    ...Array(2).fill(["NUM.OPS.02", "R31", true, []]),
  ];
  for (const [skill, rung, right, mistakes] of answers) {
    await sql`
      insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,
                                  observed_at, confirmed_by)
      values (${tenant_id}, ${id}, ${skill}, ${rung}, ${right}, ${mistakes}, 'item', now(), 'e2e')`;
  }
  await sql`select rebuild_child_skill_state(${id}::uuid)`;
  return id;
}

async function clearUp(id: string) {
  await sql`delete from item_exposure where child_id = ${id}`;
  await sql`delete from sheet_instance where child_id = ${id}`;
  await sql`delete from sheet_template where child_id = ${id}`;
}

/** What printing writes for the child: a preview, and every different draw of it, writes none of it. */
async function written(id: string) {
  const [r] = await sql<{ sheets: number; templates: number; seen: number }[]>`
    select (select count(*)::int from sheet_instance where child_id = ${id}) as sheets,
           (select count(*)::int from sheet_template where child_id = ${id}) as templates,
           (select count(*)::int from item_exposure where child_id = ${id}) as seen`;
  return r;
}

/** The questions a paper prints, in order, by their bank keys. */
async function printed(qr: string): Promise<string[]> {
  const rows = await sql<{ item_key: string }[]>`
    select i.item_key from sheet_instance si join sheet_template st on st.id = si.sheet_template_id,
      unnest(st.item_ids) with ordinality as x(id, ord) join item i on i.id = x.id
    where si.qr_code = ${qr} order by x.ord`;
  return rows.map((r) => r.item_key);
}

/** The questions on screen in `where`, in order, by their bank keys. */
const shown = (where: Locator) => where.locator("li[data-item]").evaluateAll((li) => li.map((x) => x.getAttribute("data-item")!));
const nothing = { sheets: 0, templates: 0, seen: 0 };
const qrIn = (page: Page, key: string) => new URL(page.url()).searchParams.get(key)!;

let child = "";
test.beforeAll(async () => {
  child = await testChild();
  await clearUp(child);
});
test.beforeEach(async () => clearUp(child));
test.afterAll(async () => {
  await clearUp(child);
  await sql.end();
});

test("the child's page shows the home assessment's questions before it prints, and different questions make no paper", async ({ page }) => {
  await page.goto(`/growth/${child}`);
  const panel = page.getByRole("region", { name: "Home assessment" });
  // the questions themselves, under their skill and level, before anything prints
  const questions = panel.getByRole("list", { name: /^3-digit − 3-digit · (Easy|Medium|Hard|Advance)$/ });
  await expect(questions.getByRole("listitem")).toHaveCount(12);
  const first = await shown(questions);
  await panel.scrollIntoViewIfNeeded();
  await panel.screenshot({ path: `${SHOTS}/1-child-page.png` });

  await panel.getByRole("link", { name: "Different questions" }).click();
  await expect(page).toHaveURL(/\?draw=1$/);
  await expect(questions.getByRole("listitem")).toHaveCount(12);
  const other = await shown(questions);
  expect(other).not.toEqual(first);
  expect(await written(child)).toEqual(nothing);

  // printing after a preview prints exactly the questions previewed, never a fresh draw
  await panel.getByRole("button", { name: "Approve this home assessment" }).click();
  await expect(page).toHaveURL(/\/papers\/review\/CS[0-9A-F]{6}$/);
  expect(await printed(page.url().split("/").pop()!)).toEqual(other);
});

test("a class's home assessments show each child's questions before approval, and different questions make no paper", async ({ page }) => {
  await page.goto(`/make/${SECTION}`);
  const row = page.locator(`tr[data-child="${child}"]`);
  await row.getByText("Its questions").click();
  const questions = row.getByRole("list", { name: /^3-digit − 3-digit · / });
  await expect(questions.getByRole("listitem")).toHaveCount(12);
  const first = await shown(questions);
  await page.getByRole("table", { name: "Each child's home assessment" }).screenshot({ path: `${SHOTS}/2-class-home-assessments.png` });

  await row.getByRole("link", { name: "Different questions" }).click();
  await expect(page).toHaveURL(new RegExp(`draw=${child}(~|%7E)1$`));
  // the questions stay open on the line, now the others
  await expect.poll(() => shown(questions)).not.toEqual(first);
  await expect(questions.getByRole("listitem")).toHaveCount(12);
  const other = await shown(questions);
  expect(await written(child)).toEqual(nothing);

  await row.getByRole("button", { name: "Approve" }).click();
  await expect(page).toHaveURL(/approved=1/);
  const [made] = await sql<{ qr_code: string }[]>`select qr_code from sheet_instance where child_id = ${child} and kind = 'focus'`;
  expect(await printed(made.qr_code)).toEqual(other);
});

test("a paper chosen for one child and Make papers show different questions without making a paper, and print the ones shown", async ({ page }) => {
  // a paper chosen for one child
  await page.goto(`/make/custom?child=${child}&a=${ASK}`);
  const paper = page.getByRole("region", { name: "The paper" });
  const questions = paper.getByRole("list", { name: "3-digit − 3-digit · Easy" });
  await expect(questions.getByRole("listitem")).toHaveCount(4);
  const first = await shown(questions);
  await paper.getByRole("link", { name: "Different questions" }).click();
  await expect(page).toHaveURL(/draw=1$/);
  await expect(questions.getByRole("listitem")).toHaveCount(4);
  const other = await shown(questions);
  expect(other).not.toEqual(first);
  expect(await written(child)).toEqual(nothing);
  await paper.screenshot({ path: `${SHOTS}/3-a-paper-for-one-child.png` });
  await paper.getByRole("button", { name: "Approve and print" }).click();
  await expect(page).toHaveURL(/\/papers\/review\/CS[0-9A-F]{6}$/);
  expect(await printed(page.url().split("/").pop()!)).toEqual(other);

  // one paper for the whole class, in Make papers: its questions once, then different ones, then made as shown
  await clearUp(child);
  await page.goto(`/papers/make?class=${SECTION}&of=${SECTION}&kind=practice&way=same&picked=1&c=${child}&a=${ASK}`);
  const papers = page.getByRole("region", { name: "The papers" });
  const all = papers.getByRole("list", { name: "3-digit − 3-digit · Easy" }).first();
  await expect(all.getByRole("listitem")).toHaveCount(4);
  const before = await shown(all);
  await papers.getByRole("link", { name: "Different questions" }).click();
  await expect(page).toHaveURL(/draw=1$/);
  await expect(all.getByRole("listitem")).toHaveCount(4);
  const after = await shown(all);
  expect(after).not.toEqual(before);
  expect(await written(child)).toEqual(nothing);
  await papers.locator(".panel").screenshot({ path: `${SHOTS}/4-make-papers.png` });
  await papers.getByRole("button", { name: "Make and approve 1 class practice paper" }).click();
  await expect(page).toHaveURL(/made=CS[0-9A-F]{6}/);
  expect(await printed(qrIn(page, "made"))).toEqual(after);
});
