import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { sql, TENANT_SLUG } from "./db";

// The one-time link that lets a person set their own password: "Forgot your password?", and the first link a new
// member of staff is sent (goals/auth-email-password.yaml).
//
// What is kept is a sha-256 of the token, never the token: the rows are no use to anyone who reads them, and 32 random
// bytes need no slow hash. A link is open while it is neither used nor closed and its time is not up; asking for a new
// one, using one, or changing a password closes every other link that person has. Every limit is a threshold row.

/** The token that travels in the email, and the hash the row holds. 32 bytes, from the system's own randomness. */
export function newToken(): { token: string; hash: string } {
  const token = randomBytes(32).toString("base64url");
  return { token, hash: tokenHash(token) };
}

export function tokenHash(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

/** The address a request came from, as an HMAC under the site's secret: a limit can count it without it being kept. */
export function addressMark(address: string): string {
  const secret = process.env.AUTH_SECRET ?? "";
  return createHmac("sha256", secret).update(address).digest("hex").slice(0, 32);
}

export type Purpose = "reset" | "first";

/** The cookie the link's token is moved into, so the token leaves the address bar on the first click: it is then in no
 *  history, no bookmark and no further log line. Short-lived, and gone the moment the password is set. */
export const LINK_COOKIE = "cs_pwlink";
export const LINK_COOKIE_MINUTES = 30;

/** What the forgotten-password form always answers, whether or not that email is anyone's. */
export const SAME_EITHER_WAY = "If that email is a staff email, we have sent a link";

/** Makes a link for this email and returns the token the email carries. Every link that person had open is closed
 *  first, so the newest link is the only one that works. */
export async function makeLink(email: string, purpose: Purpose): Promise<string> {
  await closeLinks(email);
  const { token, hash } = newToken();
  await sql`
    insert into password_link (tenant_id, email, token_hash, purpose, expires_at)
    select t.id, ${email}, ${hash}, ${purpose},
           now() + case when ${purpose} = 'first'
             then make_interval(days => (select value from threshold where key = 'password_link.first_days')::int)
             else make_interval(mins => (select value from threshold where key = 'password_link.reset_minutes')::int)
           end
    from tenant t where t.slug = ${TENANT_SLUG}`;
  return token;
}

/** Closes every open link of this person's: nothing older than their newest ask, or than their new password, opens. */
export async function closeLinks(email: string): Promise<void> {
  await sql`
    update password_link set closed_at = now()
    where email = ${email} and closed_at is null and used_at is null`;
}

/** What became of the email, written on the link's own row. Never why it failed: that could carry an address. */
export async function sayMail(hash: string, mail: string): Promise<void> {
  await sql`update password_link set mail = ${mail} where token_hash = ${hash}`;
}

/** The staff email a token opens, or null when the token is unknown, used, closed or out of time. The row is found by
 *  the hash, and the hash found is then compared with the one asked for in constant time. */
export async function emailFor(token: string): Promise<string | null> {
  if (!token) return null;
  const want = tokenHash(token);
  const [row] = await sql<{ email: string; token_hash: string }[]>`
    select email, token_hash from password_link
    where token_hash = ${want} and used_at is null and closed_at is null and expires_at > now()`;
  if (!row) return null;
  const a = Buffer.from(row.token_hash);
  const b = Buffer.from(want);
  return a.length === b.length && timingSafeEqual(a, b) ? row.email : null;
}

/** Marks the token used. Everything else of that person's is closed by the password itself (`setPassword`). */
export async function spend(token: string): Promise<void> {
  await sql`update password_link set used_at = now() where token_hash = ${tokenHash(token)} and used_at is null`;
}

/** Every "Forgot your password?" is written down, whether or not the email is anyone's, and the form is refused past
 *  `password_ask.max_per_email` for one email or `password_ask.max_per_ip` from one address inside the window. The
 *  person reads the same words either way, so a refusal never says who is staff. */
export async function askedTooOften(email: string, address: string): Promise<boolean> {
  const [row] = await sql<{ refused: boolean | null }[]>`
    with window_start as (
      select now() - make_interval(mins => (select value from threshold where key = 'password_ask.window_minutes')::int) as t
    )
    select (select count(*) from password_ask, window_start
             where email = ${email} and created_at > window_start.t)
           >= (select value from threshold where key = 'password_ask.max_per_email')
        or (select count(*) from password_ask, window_start
             where ip = ${addressMark(address)} and created_at > window_start.t)
           >= (select value from threshold where key = 'password_ask.max_per_ip') as refused`;
  return Boolean(row?.refused);
}

export async function recordAsk(email: string, address: string): Promise<void> {
  await sql`
    insert into password_ask (tenant_id, email, ip)
    select id, ${email}, ${addressMark(address)} from tenant where slug = ${TENANT_SLUG}`;
}
