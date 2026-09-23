"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { type Band, type Difficulty, levelsOf } from "@/lib/queries";

const CODE = /^[A-Z0-9._]+$/;

/** A person changes a skill's words — its name, what the child can do, and each level in a
 *  sentence. The rule each question is checked against is not a teacher's field and is not on this
 *  form; it is kept exactly as it was. Any change withdraws the approval (trigger
 *  `skill_set_version_on_change`), so whoever approves next has read these words. */
export async function saveWords(formData: FormData): Promise<void> {
  await requireStaff();
  const code = String(formData.get("code") ?? "");
  if (!CODE.test(code)) redirect("/");
  const name = String(formData.get("name") ?? "").trim().slice(0, 80);
  const outcome = String(formData.get("learning_objective") ?? "").trim().slice(0, 400);
  const [row] = await sql<{ difficulty: Record<Difficulty, Band> }[]>`select difficulty from skill_set where code = ${code}`;
  if (!row) redirect("/");
  // only the levels the skill defines: 1-digit − 1-digit has no Hard, and saving must not make one
  const levels = levelsOf(row);
  const words = Object.fromEntries(
    levels.map((d) => [d, String(formData.get(`words:${d}`) ?? "").trim().slice(0, 400)]),
  ) as Record<Difficulty, string>;
  if (!name || !outcome || levels.some((d) => !words[d])) redirect(`/skill-sets/${code}/edit?error=required`);
  const difficulty = Object.fromEntries(
    levels.map((d) => [d, { ...row.difficulty[d], words: words[d] }]),
  ) as Record<Difficulty, Band>;
  await sql`
    update skill_set set name = ${name}, learning_objective = ${outcome},
      difficulty = ${sql.json(difficulty as never)}, updated_at = now()
    where code = ${code}`;
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?saved=1`);
}

/** A named person approves skills exactly as they read them — one from its own page, or every
 *  waiting skill from the approval page. Only skills still waiting are touched: an approval never
 *  lands on words changed since the page was opened, because a change sets the skill back to
 *  waiting and bumps its version, and the form carries the version it showed. */
export async function approveSkills(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const shown = formData.getAll("code").map(String).filter((c) => CODE.test(c));
  const versions = formData.getAll("version").map(Number);
  const back = String(formData.get("back") ?? "/");
  const onlyTable = !shown.length && typeof formData.get("charges_table") === "string";
  if ((!shown.length && !onlyTable) || versions.length !== shown.length || versions.some((v) => !Number.isInteger(v))) redirect("/");
  const approved = await sql<{ code: string }[]>`
    update skill_set s set status = 'ratified', ratified_by = ${me.name}, updated_at = now()
    from unnest(${shown}::text[], ${versions}::int[]) as v(code, version)
    where s.code = v.code and s.version = v.version and s.status = 'draft'
    returning s.code`;
  // The table of what a mistake charges, approved exactly as the page showed it: if it changed since,
  // the update matches nothing and it keeps waiting. `::text` first: postgres.js sends a string it
  // sees bound for jsonb as a JSON string, which would never equal the table.
  const table = formData.get("charges_table");
  if (typeof table === "string" && table) {
    await sql`
      update config set value = jsonb_build_object('by', ${me.name}::text, 'table', t.value), updated_at = now()
      from (select value from config where key = 'skills.charges_by_kind') t
      where config.key = 'skills.charges_by_kind.approved' and t.value = ${table}::text::jsonb`;
  }
  revalidatePath("/");
  for (const c of approved) revalidatePath(`/skill-sets/${c.code}`);
  // Only back to the map or a skill page: a return address from a form is never trusted to leave the site.
  redirect(`${/^\/(skill-sets\/[A-Z0-9._]+)?$/.test(back) ? back : "/"}?approved=${approved.length}`);
}
