import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { sql, TENANT_SLUG } from "./db";
import { deadline } from "./deadline";
import { staffList, type Staff } from "./queries";
import { devBypass, SESSION_COOKIE, SESSION_DAYS, sessionEmail, sessionValue } from "./session-cookie";

// Who is signed in, without the password hash: a session can reach a client component, and the hash must not.
export type Session = Omit<Staff, "password"> & { devBypass: boolean };

// `scrypt$salt$hash`, both hex. scrypt is in node's standard library, so no dependency and no
// bcrypt build step; the salt is per person so two people with the same password differ.
export function hashPassword(password: string, salt = randomBytes(16).toString("hex")): string {
  return `scrypt$${salt}$${scryptSync(password, salt, 64).toString("hex")}`;
}

function passwordMatches(password: string, stored: string | undefined): boolean {
  const [scheme, salt, want] = (stored ?? "").split("$");
  if (scheme !== "scrypt" || !salt || !want) return false;
  const got = scryptSync(password, salt, 64);
  const expected = Buffer.from(want, "hex");
  return got.length === expected.length && timingSafeEqual(got, expected);
}

export async function startSession(email: string): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, sessionValue(email), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_DAYS * 86_400,
  });
}

export async function endSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

// A password is not guessed by trying: past `sign_in.max_failures` wrong ones for an email inside
// `sign_in.window_minutes`, that email waits out the window (goals/p2-live-recovers.yaml).
// ponytail: per email, so anyone can make a known email wait; add a limit per address if that is ever used.
export async function signInRefused(email: string): Promise<boolean> {
  const [row] = await sql<{ refused: boolean | null }[]>`
    select (select count(*) from sign_in_failure where email = ${email} and created_at > now()
              - make_interval(mins => (select value from threshold where key = 'sign_in.window_minutes')::int))
           >= (select value from threshold where key = 'sign_in.max_failures') as refused`;
  return Boolean(row?.refused);
}

export async function signInFailed(email: string): Promise<void> {
  await sql`insert into sign_in_failure (tenant_id, email) select id, ${email} from tenant where slug = ${TENANT_SLUG}`;
}

/** The staff member whose password matched, or null. Both misses read the same to the caller so
 * the form cannot be used to find out which emails are on the list. */
export async function verifyStaff(email: string, password: string): Promise<Staff | null> {
  const staff = (await staffList()).find((s) => s.email.toLowerCase() === email.trim().toLowerCase());
  return staff && passwordMatches(password, staff.password) ? staff : null;
}

// Who is signed in, or null when the cookie is missing, edited, expired or names nobody on the
// staff list. A database that does not answer is NOT "signed out": it throws, and the person reads
// that the database did not answer (app/error.tsx). Swallowing it once sent a signed-in founder to
// the login page during an outage, which read as a broken password. Once per request, however many
// pages, layouts and data reads ask.
export const currentStaff = cache(async (): Promise<Session | null> => {
  if (devBypass()) return { email: "dev@local", name: "Dev bypass", role: "coordinator", devBypass: true };
  const email = sessionEmail((await cookies()).get(SESSION_COOKIE)?.value);
  if (!email) return null;
  const staff = (await deadline(staffList())).find((s) => s.email.toLowerCase() === email.toLowerCase());
  // named fields, never the record: the password hash stays on the server
  return staff ? { email: staff.email, name: staff.name, role: staff.role, devBypass: false } : null;
});

// For every page, route and server action: the signed-in staff member, or a redirect to /login. Each calls it
// itself; a layout's check alone is not enough (Next 16's auth guide, "Layouts and auth checks").
export async function requireStaff(): Promise<Session> {
  const me = await currentStaff();
  if (me) return me;
  redirect("/login");
}
