import common from "../../../supabase/seed/common_passwords.json";
import { hashPassword, scryptCost } from "./auth";
import { sql } from "./db";
import { closeLinks } from "./password-links";

// What makes a new password good enough (goals/auth-email-password.yaml). The length is a threshold row and the list of
// the commonest passwords is a seed file, so neither is a number or a list inside code (rule 1). Three rules, no more:
// Nimish, 26 Oct 2026, "keep it simple" — no character classes, no expiry, no history.
const COMMON = new Set(common.passwords.map((p) => p.toLowerCase()));

/** Why this password cannot be used, in the words the person reads, or null when it can. */
export async function passwordProblem(password: string, email: string): Promise<string | null> {
  const [row] = await sql<{ least: number }[]>`
    select (select value from threshold where key = 'password.min_length')::int as least`;
  const least = row?.least ?? 10;
  if (password.length < least) return `Use at least ${least} characters.`;
  if (password.trim().toLowerCase() === email.trim().toLowerCase()) {
    return "That is your email address. Use something else.";
  }
  if (COMMON.has(password.toLowerCase())) return "That password is one of the most common ones. Use another.";
  return null;
}

/** Gives this person their new password and ends every session of theirs that is already open: the staff row carries
 *  the hash `lib/auth.ts` checks and the moment it was set, which no cookie made before it survives (`currentStaff`).
 *  One statement, so a password written while a coordinator saves someone's classes cannot undo either (lib/db.ts).
 *  Their open links are closed too, used or not. */
export async function setPassword(email: string, password: string): Promise<void> {
  const now = new Date();
  const mine = { password: hashPassword(password, await scryptCost()), password_set_at: now.toISOString() };
  await sql`
    update config set value = (
      select coalesce(jsonb_agg(case when lower(p->>'email') = ${email.toLowerCase()} then p || ${sql.json(mine)} else p end), '[]'::jsonb)
      from jsonb_array_elements(value) p)
    where key = 'app.staff'`;
  await closeLinks(email);
}
