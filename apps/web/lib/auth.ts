import { createHmac, randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { deadline } from "./deadline";
import { staffList, type Staff } from "./queries";

export type Session = Staff & { devBypass: boolean };

const COOKIE = "cs_staff";
const DAYS = 30;

// True only in development and only when asked for. Production never bypasses (auth rule: a
// disabled gate is a ship blocker).
export function devBypass(): boolean {
  return process.env.NODE_ENV === "development" && process.env.AUTH_DEV_BYPASS === "1";
}

function secret(): string {
  const s = process.env.AUTH_SECRET;
  if (!s || s.length < 32) throw new Error("AUTH_SECRET is missing or too short (32+ chars).");
  return s;
}

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

// `email.expiry.signature` — the signature is what stops a cookie being edited by hand.
function sign(value: string): string {
  return createHmac("sha256", secret()).update(value).digest("hex");
}

function readCookie(raw: string | undefined): string | null {
  const [email, expiry, mac] = (raw ?? "").split(".");
  if (!email || !expiry || !mac) return null;
  const want = Buffer.from(sign(`${email}.${expiry}`));
  const got = Buffer.from(mac);
  if (want.length !== got.length || !timingSafeEqual(want, got)) return null;
  if (Number(expiry) < Date.now()) return null;
  return Buffer.from(email, "base64url").toString();
}

export async function startSession(email: string): Promise<void> {
  const expiry = String(Date.now() + DAYS * 86_400_000);
  const body = `${Buffer.from(email).toString("base64url")}.${expiry}`;
  (await cookies()).set(COOKIE, `${body}.${sign(body)}`, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: DAYS * 86_400,
  });
}

export async function endSession(): Promise<void> {
  (await cookies()).delete(COOKIE);
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
// the login page during an outage, which read as a broken password.
export async function currentStaff(): Promise<Session | null> {
  if (devBypass()) return { email: "dev@local", name: "Dev bypass", role: "coordinator", devBypass: true };
  const email = readCookie((await cookies()).get(COOKIE)?.value);
  if (!email) return null;
  const staff = (await deadline(staffList())).find((s) => s.email.toLowerCase() === email.toLowerCase());
  return staff ? { ...staff, devBypass: false } : null;
}

// For pages and server actions: the signed-in staff member, or a redirect to /login.
export async function requireStaff(): Promise<Session> {
  const me = await currentStaff();
  if (me) return me;
  redirect("/login");
}
