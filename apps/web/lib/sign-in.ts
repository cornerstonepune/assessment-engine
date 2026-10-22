import { sql } from "./db";

// Who Google may let in, a row (`config.app.sign_in`): the school's Google Workspace domain, and the role a school
// email signing in for the first time is given. Nimish, 2026-10-22: "no one can log in without the Cornerstone email
// ID … right now, we just put me as the admin and everyone else as the educator."
export type SignInRule = { domain: string; new_staff_role: string };

/** The rule, or null before the row is loaded: then no one is let in, and the sign-in page says it is not set up. */
export async function signInRule(): Promise<SignInRule | null> {
  const [row] = await sql<{ value: SignInRule }[]>`select value from config where key = 'app.sign_in'`;
  return row?.value?.domain && row.value.new_staff_role ? row.value : null;
}

/** Puts a school email that is not yet on the staff list on it, with the rule's role and no class; someone already on
 * it keeps their role, name and classes. One statement, so two first sign-ins at once add the person once. */
export async function joinStaff(email: string, name: string, role: string): Promise<void> {
  await sql`
    update config set value = value || ${sql.json([{ email, name, role, classes: [] }])}
    where key = 'app.staff'
      and not exists (select 1 from jsonb_array_elements(value) s where lower(s ->> 'email') = ${email})`;
}
