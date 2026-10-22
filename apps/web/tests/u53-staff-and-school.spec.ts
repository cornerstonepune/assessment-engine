/**
 * U53 — Staff and School (goals/uxn2-staff-and-school.yaml). Nimish, 2026-10-22: "the staff table of who teaches which
 * class and subject is edited on a Staff page, not by commands", and "Ayush ... has the account". A coordinator ticks the
 * classes a member of staff teaches and saves; the School page shows each class with who teaches it.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";
import { aClass } from "./rows";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
const CLASS = "UXN2-CLASS";
const PERSON = {
  email: "uxn2.ayush@cornerstone.test",
  name: "Ayush Test",
  role: "educator",
  password: "scrypt$keep$me",
  classes: [] as string[],
};

test.use({ viewport: { width: 1440, height: 900 } });

test.beforeAll(async () => {
  await aClass(sql, CLASS, "G3", ["Uma", "Vik"]);
  await sql`update config set value = value || ${sql.json([PERSON])} where key = 'app.staff' and not value @> ${sql.json([{ email: PERSON.email }])}`;
});
test.afterAll(async () => {
  await sql`update config set value = (select coalesce(jsonb_agg(p), '[]'::jsonb) from jsonb_array_elements(value) p where p ->> 'email' <> ${PERSON.email}) where key = 'app.staff'`;
  await sql.end();
});

const classesOf = async () =>
  (
    await sql<
      { c: string[] }[]
    >`select p -> 'classes' as c from config, jsonb_array_elements(value) p where key = 'app.staff' and p ->> 'email' = ${PERSON.email}`
  )[0].c;

test("a coordinator ticks a person's classes on the Staff page and the list keeps them, and the rest of the person", async ({
  page,
}) => {
  await page.goto("/staff");
  const table = page.getByRole("table", { name: "Staff" });
  const row = table.locator(`tr[data-person="${PERSON.email}"]`);
  await expect(row).toContainText("No class yet");
  await row.locator("summary").click();
  await row.getByLabel(CLASS).check();
  await row.getByRole("button", { name: "Save the classes" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Ayush Test’s classes are saved",
  );
  expect(await classesOf()).toEqual([CLASS]);
  const [kept] = await sql<
    { password: string; role: string }[]
  >`select p ->> 'password' as password, p ->> 'role' as role from config, jsonb_array_elements(value) p where key = 'app.staff' and p ->> 'email' = ${PERSON.email}`;
  expect(kept).toEqual({ password: PERSON.password, role: "educator" });
  // no password hash is ever on the page
  expect(await page.content()).not.toContain("scrypt$");
  await expect(
    table.locator(`tr[data-person="${PERSON.email}"]`),
  ).toContainText(CLASS);
});

test("a class no child is in refuses everything, and the filter row finds a person", async ({
  page,
}) => {
  await page.goto("/staff?role=educator&q=ayush");
  await expect(page.locator("[data-filterbar]")).toBeVisible();
  const row = page
    .getByRole("table", { name: "Staff" })
    .locator(`tr[data-person="${PERSON.email}"]`);
  await expect(row).toBeVisible();
  await row.locator("summary").click();
  await row.locator("form").evaluate((f) => {
    const box = document.createElement("input");
    box.type = "hidden";
    box.name = "class";
    box.value = "NO-SUCH-CLASS";
    f.appendChild(box);
  });
  await row.getByRole("button", { name: "Save the classes" }).click();
  await expect(page.getByRole("status")).toContainText(
    "no child is in NO-SUCH-CLASS",
  );
  expect(await classesOf(), "nothing changed").toEqual([CLASS]);
});

test("School shows each class with its grade, its children and who teaches it", async ({
  page,
}) => {
  await page.goto("/school");
  const row = page
    .getByRole("table", { name: "Classes" })
    .locator("tbody tr", { hasText: CLASS });
  await expect(row).toContainText("Grade 3");
  await expect(row).toContainText("Ayush Test");
  await expect(row.locator("td").nth(2)).toHaveText("2");
  await expect(
    page.getByRole("link", { name: "School and staff" }),
  ).toBeVisible();
});
