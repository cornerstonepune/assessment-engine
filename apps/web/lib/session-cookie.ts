import { createHmac, timingSafeEqual } from "node:crypto";

// The staff session cookie, written by lib/auth.ts and read the same way by proxy.ts before any page renders.
// `base64url(email).expiry.hmac`: the signature is what stops a cookie being edited by hand. Nothing here touches the
// database, so the proxy can turn away a request with no good cookie on its own; the page's requireStaff still looks
// the person up on the staff list (goals/p0-every-page-checks-who-asks.yaml).

export const SESSION_COOKIE = "cs_staff";
export const SESSION_DAYS = 30;

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

function sign(value: string): string {
  return createHmac("sha256", secret()).update(value).digest("hex");
}

/** The cookie's value for this email, good for SESSION_DAYS from `now`. */
export function sessionValue(email: string, now = Date.now()): string {
  const body = `${Buffer.from(email).toString("base64url")}.${now + SESSION_DAYS * 86_400_000}`;
  return `${body}.${sign(body)}`;
}

/** The email a cookie names, or null when it is missing, edited or expired. */
export function sessionEmail(raw: string | undefined, now = Date.now()): string | null {
  const [email, expiry, mac] = (raw ?? "").split(".");
  if (!email || !expiry || !mac) return null;
  const want = Buffer.from(sign(`${email}.${expiry}`));
  const got = Buffer.from(mac);
  if (want.length !== got.length || !timingSafeEqual(want, got)) return null;
  if (Number(expiry) < now) return null;
  return Buffer.from(email, "base64url").toString();
}
