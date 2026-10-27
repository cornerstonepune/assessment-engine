import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { sql, TENANT_SLUG } from "./db";
import { deadline } from "./deadline";
import { staffList, type Staff } from "./queries";
import { devBypass, SESSION_COOKIE, SESSION_DAYS, sessionEmail, sessionIssued, sessionValue } from "./session-cookie";

// Who is signed in, without the password hash: a session can reach a client component, and the hash must not.
/** Who is signed in. No view is kept: a person sees the classes and subjects their staff row names, and each page narrows
 *  further with its own filters (goals/nav3_what_needs_doing.yaml, Nimish 26 Oct 2026). Never a permission (lib/access.ts). */
export type Session = Omit<Staff, "password" | "password_set_at"> & { devBypass: boolean };

// `scrypt$n$salt$hash`: the work it took is written beside it, so the cost can be raised later without locking
// everyone out — a hash made before this (`scrypt$salt$hash`) took node's own default and still reads. scrypt is in
// node's standard library, so no dependency and no bcrypt build step; the salt is per person so two people with the
// same password differ. How hard a new password is hashed is the `password.scrypt_n` row (rule 1), not a number here.
const NODE_DEFAULT_N = 16_384;
const KEY_BYTES = 64;
// scrypt needs 128 · n · r bytes to work in — 1024n at r=8, well over node's own 32 MB ceiling once n passes 32768.
const work = (n: number) => ({ N: n, r: 8, p: 1, maxmem: 1152 * n });

export function hashPassword(password: string, n: number, salt = randomBytes(16).toString("hex")): string {
  return `scrypt$${n}$${salt}$${scryptSync(password, salt, KEY_BYTES, work(n)).toString("hex")}`;
}

/** How hard a password set now is hashed: `password.scrypt_n`, a row, so raising it needs no deploy. */
export async function scryptCost(): Promise<number> {
  const [row] = await sql<{ n: number }[]>`
    select (select value from threshold where key = 'password.scrypt_n')::int as n`;
  return row?.n ?? NODE_DEFAULT_N;
}

function passwordMatches(password: string, stored: string | undefined): boolean {
  const parts = (stored ?? "").split("$");
  const [scheme, n, salt, want] = parts.length === 4 ? parts : [parts[0], String(NODE_DEFAULT_N), parts[1], parts[2]];
  if (scheme !== "scrypt" || !salt || !want || !Number(n)) return false;
  const got = scryptSync(password, salt, KEY_BYTES, work(Number(n)));
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
 * the form cannot be used to find out which emails are on the list — and take the same time: an email nobody holds
 * used to come back while a staff email was still being hashed, which told anyone watching the clock who is staff
 * (goals/auth-email-password.yaml). A miss hashes the same password against a salt of its own and throws it away. */
export async function verifyStaff(email: string, password: string): Promise<Staff | null> {
  const staff = (await staffList()).find((s) => s.email.toLowerCase() === email.trim().toLowerCase());
  const stored = staff?.password ?? (await decoy());
  return passwordMatches(password, stored) && staff ? staff : null;
}

// The hash an email nobody holds is checked against: made once per process (it is no secret, and nothing is told
// about it), so a miss costs exactly the one hashing a hit costs.
let made: { n: number; hash: string } | null = null;
async function decoy(): Promise<string> {
  const n = await scryptCost();
  if (made?.n !== n) made = { n, hash: hashPassword("no password of anyone's", n) };
  return made.hash;
}

// Who is signed in, or null when the cookie is missing, edited, expired or names nobody on the
// staff list. A database that does not answer is NOT "signed out": it throws, and the person reads
// that the database did not answer (app/error.tsx). Swallowing it once sent a signed-in founder to
// the login page during an outage, which read as a broken password. Once per request, however many
// pages, layouts and data reads ask.
export const currentStaff = cache(async (): Promise<Session | null> => {
  if (devBypass()) return { id: undefined, email: "dev@local", name: "Dev bypass", role: "coordinator", classes: [], subjects: [], devBypass: true };
  const raw = (await cookies()).get(SESSION_COOKIE)?.value;
  const email = sessionEmail(raw);
  if (!email) return null;
  const staff = (await deadline(staffList())).find((s) => s.email.toLowerCase() === email.toLowerCase());
  // named fields, never the record: the password hash stays on the server
  if (!staff) return null;
  // A password set after this cookie was signed ends the session it belongs to, wherever it is open
  // (goals/auth-email-password.yaml: "every other open session of that person is ended").
  const set = staff.password_set_at ? Date.parse(staff.password_set_at) : NaN;
  if (!Number.isNaN(set) && set > (sessionIssued(raw) ?? 0)) return null;
  return { id: staff.id, email: staff.email, name: staff.name, role: staff.role, classes: staff.classes ?? [], subjects: staff.subjects ?? [], devBypass: false };
});

// For every page, route and server action: the signed-in staff member, or a redirect to /login. Each calls it
// itself; a layout's check alone is not enough (Next 16's auth guide, "Layouts and auth checks").
export async function requireStaff(): Promise<Session> {
  const me = await currentStaff();
  if (me) return me;
  redirect("/login");
}
