"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { DIFFICULTIES } from "@/lib/queries";

const ALLOWED_FORMATS = ["column_grid", "bare_sum", "missing_number", "word_1step"];

function lines(v: FormDataEntryValue | null): string[] {
  return String(v ?? "").split("\n").map((s) => s.trim()).filter(Boolean);
}

export async function saveSkillSet(formData: FormData): Promise<void> {
  await requireStaff();
  const code = String(formData.get("code") ?? "");
  if (!/^[A-Z0-9.]+$/.test(code)) redirect("/");

  const name = String(formData.get("name") ?? "").trim();
  const objective = String(formData.get("learning_objective") ?? "").trim();
  if (!name || !objective) redirect(`/skill-sets/${code}?error=required`);

  const formats = formData.getAll("formats").map(String).filter((f) => ALLOWED_FORMATS.includes(f));
  const misconceptions = formData.getAll("misconception_codes").map(String).filter((c) => /^M_[A-Z0-9_]+$/.test(c));

  // The rule a teacher sets in plain fields becomes the check the verifier enforces. Keys the
  // form does not know (an engineer's addition) are carried over from the existing check untouched.
  const difficulty: Record<string, { words: string; check: Record<string, unknown> }> = {};
  for (const d of DIFFICULTIES) {
    const words = String(formData.get(`words:${d}`) ?? "").trim();
    let existing: Record<string, unknown> = {};
    try {
      existing = JSON.parse(String(formData.get(`existing:${d}`) ?? "{}"));
    } catch {
      existing = {};
    }
    const op = String(formData.get(`op:${d}`) ?? "");
    const top = Number(formData.get(`top:${d}`));
    const bottom = Number(formData.get(`bottom:${d}`));
    const regroups = formData.getAll(`regroups:${d}`).map(Number).filter((n) => Number.isInteger(n) && n >= 0 && n <= 3);
    const zeros = String(formData.get(`zeros:${d}`) ?? "any");
    const maxTotal = Number(formData.get(`max_total:${d}`));
    if (!["+", "-", "×"].includes(op) || ![1, 2, 3, 4, 5].includes(top) || ![1, 2, 3, 4, 5].includes(bottom) || regroups.length === 0) {
      redirect(`/skill-sets/${code}?error=check&band=${d}`);
    }
    const check: Record<string, unknown> = { ...existing, op, digits: [top, bottom], regroups: regroups.sort() };
    delete check.no_zero_top;
    delete check.across_zero;
    delete check.max_total;
    if (zeros === "none") check.no_zero_top = true;
    if (zeros === "across") check.across_zero = true;
    if (zeros === "not_across") check.across_zero = false;
    if (Number.isInteger(maxTotal) && maxTotal > 0) check.max_total = maxTotal;
    difficulty[d] = { words, check };
  }

  await sql`
    update skill_set set name = ${name}, learning_objective = ${objective},
      philosophy = ${lines(formData.get("philosophy"))}, formats = ${formats},
      misconception_codes = ${misconceptions}, difficulty = ${sql.json(difficulty as never)},
      updated_at = now()
    where code = ${code}`;
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?saved=1`);
}

export async function ratifySkillSet(formData: FormData): Promise<void> {
  const me = await requireStaff();
  const code = String(formData.get("code") ?? "");
  if (!/^[A-Z0-9.]+$/.test(code)) redirect("/");
  await sql`update skill_set set status = 'ratified', ratified_by = ${me.email}, updated_at = now() where code = ${code}`;
  revalidatePath("/");
  revalidatePath(`/skill-sets/${code}`);
  redirect(`/skill-sets/${code}?ratified=1`);
}
