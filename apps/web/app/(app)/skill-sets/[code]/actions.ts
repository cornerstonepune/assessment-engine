"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { deciding } from "@/lib/decides";
import { sql } from "@/lib/db";
import { type Band, DIFFICULTIES, type Difficulty, levelsOf } from "@/lib/queries";

const CODE = /^[A-Z0-9._]+$/;
// the approval page under its own choices (goals/ui6a-approve-filtered.yaml), and nothing else
const APPROVE_PAGE = /^\/skill-sets\/approve(\?(grade|topic|taught)=[\w.-]+(&(grade|topic|taught)=[\w.-]+)*)?$/;

/** A person changes a skill's words — its name, what the child can do, and each level in a
 *  sentence. The rule each question is checked against is not a teacher's field and is not on this
 *  form; it is kept exactly as it was. Any change withdraws the approval (trigger
 *  `skill_set_version_on_change`), so whoever approves next has read these words. */
export async function saveWords(formData: FormData): Promise<void> {
  await deciding("skill_drafts");
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
  const me = await deciding("skills");
  let shown = formData.getAll("code").map(String).filter((c) => CODE.test(c));
  let versions = formData.getAll("version").map(Number);
  let back = String(formData.get("back") ?? "/");
  // one skill of the page, approved on its own (goals/ui3-curriculum.yaml): its own code and version, and back to the
  // page, under the choices it was opened with, to approve the next; the table of what a mistake charges waits for its
  // own approval
  const only = String(formData.get("only") ?? "");
  if (CODE.test(only)) {
    const i = shown.indexOf(only);
    if (i < 0) redirect("/");
    [shown, versions, back] = [[only], [versions[i]], APPROVE_PAGE.test(back) ? back : "/skill-sets/approve"];
  }
  const onlyTable = !shown.length && typeof formData.get("charges_table") === "string";
  if ((!shown.length && !onlyTable) || versions.length !== shown.length || versions.some((v) => !Number.isInteger(v))) redirect("/");
  const approved = await sql<{ code: string }[]>`
    update skill_set s
    set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', ${me.name}::text, 'at', now()))
                          from jsonb_object_keys(s.difficulty) k),
        updated_at = now()
    from unnest(${shown}::text[], ${versions}::int[]) as v(code, version)
    where s.code = v.code and s.version = v.version and s.status = 'draft'
    returning s.code`;
  // The table of what a mistake charges, approved exactly as the page showed it: if it changed since,
  // the update matches nothing and it keeps waiting. `::text` first: postgres.js sends a string it
  // sees bound for jsonb as a JSON string, which would never equal the table.
  const table = CODE.test(only) ? null : formData.get("charges_table");
  const done = new URLSearchParams();
  if (shown.length) done.set("approved", String(approved.length));
  if (typeof table === "string" && table) {
    const rows = await sql`
      update config set value = jsonb_build_object('by', ${me.name}::text, 'table', t.value), updated_at = now()
      from (select value from config where key = 'skills.charges_by_kind') t
      where config.key = 'skills.charges_by_kind.approved' and t.value = ${table}::text::jsonb
      returning 1`;
    done.set("table", String(rows.length));
  }
  revalidatePath("/");
  for (const c of approved) revalidatePath(`/skill-sets/${c.code}`);
  // Only back to the map, a skill page or the approval page under its choices: a return address from a form never
  // leaves the site.
  const to = /^\/(skill-sets\/[A-Z0-9._]+)?$/.test(back) || APPROVE_PAGE.test(back) ? back : "/";
  redirect(`${to}${to.includes("?") ? "&" : "?"}${done}`);
}

/** A person says which grade teaches each level of a skill — one grade each (Nimish, 2026-09-24). Kept in its own
 *  column, not in the level's words: it moves where the level is taught, not what it asks, so the approval stays.
 *  A level in the skill's own grade is not written down; only one moved elsewhere is. */
export async function saveGrades(formData: FormData): Promise<void> {
  const me = await deciding("skill_drafts");
  const code = String(formData.get("code") ?? "");
  if (!CODE.test(code)) redirect("/");
  const [row] = await sql<{ difficulty: Record<Difficulty, Band>; band: string }[]>`
    select s.difficulty, r.band from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code
    where s.code = ${code}`;
  if (!row) redirect("/");
  const moved = Object.fromEntries(
    levelsOf(row)
      .map((d) => [d, String(formData.get(`grade:${d}`) ?? "")] as const)
      .filter(([, g]) => /^G[1-9]\+?$/.test(g) && g !== row.band),
  );
  // in the mover's name (goals/c1-whole-curriculum.yaml): Achal reviews the progression by moving levels here
  await sql`
    update skill_set set level_band = ${sql.json(moved as never)}, level_band_by = ${me.name}, level_band_at = now()
    where code = ${code}`;
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?grades=1`);
}

/** The coordinator approves one level's questions (goals/f1d-questions-approved-per-level.yaml): that level, at the
 *  version of the skill the page showed — a level changed since keeps waiting. The skill is approved once every level
 *  it has is (trigger `skill_set_version_on_change`). */
export async function approveLevel(formData: FormData): Promise<void> {
  const me = await deciding("skills");
  const code = String(formData.get("code") ?? "");
  const version = Number(formData.get("version"));
  const level = String(formData.get("level") ?? "");
  if (!CODE.test(code) || !Number.isInteger(version) || !DIFFICULTIES.includes(level as Difficulty)) redirect("/");
  await sql`
    update skill_set set level_approved = level_approved || jsonb_build_object(${level}::text,
                           jsonb_build_object('by', ${me.name}::text, 'at', now())),
                         updated_at = now()
    where code = ${code} and version = ${version} and difficulty ? ${level}`;
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?level_approved=${level}#levels`);
}
