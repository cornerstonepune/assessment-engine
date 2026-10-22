import { CodeChallengeMethod, OAuth2Client, generateCodeVerifier, generateState } from "arctic";
import { createRemoteJWKSet, jwtVerify, type JWTPayload, type JWTVerifyGetKey } from "jose";

// Sign in with Google (goals/a1-sign-in-with-google.yaml): the authorization code flow with PKCE and state, by arctic,
// and the ID token checked here by jose against Google's published keys: signature, issuer, audience and expiry. Who
// may come in is then the school's rule alone (`schoolEmail`); the `hd` sent to Google only chooses the account picker.
// Nothing here touches the database or Next, so tests/p5-sign-in-with-google.spec.ts runs it as it is.

const GOOGLE = {
  issuers: ["https://accounts.google.com", "accounts.google.com"],
  authorize: "https://accounts.google.com/o/oauth2/v2/auth",
  token: "https://oauth2.googleapis.com/token",
  keys: "https://www.googleapis.com/oauth2/v3/certs",
};

// The Playwright run stands a fake Google on this machine (tests/fake-google.ts) and names it here. Honoured only for an
// address on the machine itself and never on Vercel, so no setting can send a real sign-in anywhere but Google.
function endpoints(): typeof GOOGLE {
  const fake = process.env.GOOGLE_FAKE_ORIGIN;
  if (!fake || process.env.VERCEL || !["127.0.0.1", "localhost"].includes(new URL(fake).hostname)) return GOOGLE;
  return { issuers: GOOGLE.issuers, authorize: `${fake}/authorize`, token: `${fake}/token`, keys: `${fake}/certs` };
}

let keys: { url: string; get: JWTVerifyGetKey } | null = null;
function googleKeys(): JWTVerifyGetKey {
  const url = endpoints().keys;
  if (keys?.url !== url) keys = { url, get: createRemoteJWKSet(new URL(url), { timeoutDuration: 5_000 }) };
  return keys.get;
}

/** Whether both Google secrets are set. Without them the sign-in page says so instead of offering a button. */
export function googleConfigured(): boolean {
  return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}

function client(redirectUri: string): OAuth2Client {
  return new OAuth2Client(process.env.GOOGLE_CLIENT_ID!, process.env.GOOGLE_CLIENT_SECRET!, redirectUri);
}

/** Where to send the person, and the state and verifier to keep until Google sends them back. */
export function googleStart(redirectUri: string, domain: string): { url: URL; state: string; verifier: string } {
  const state = generateState();
  const verifier = generateCodeVerifier();
  const url = client(redirectUri).createAuthorizationURLWithPKCE(
    endpoints().authorize, state, CodeChallengeMethod.S256, verifier, ["openid", "email", "profile"],
  );
  url.searchParams.set("hd", domain);
  url.searchParams.set("prompt", "select_account");
  return { url, state, verifier };
}

/** An ID token's claims, or a throw when its signature, issuer, audience or expiry is wrong. */
export async function verifyIdToken(idToken: string, audience: string, key: JWTVerifyGetKey = googleKeys()): Promise<JWTPayload> {
  const { payload } = await jwtVerify(idToken, key, { issuer: GOOGLE.issuers, audience, algorithms: ["RS256"] });
  return payload;
}

/** The code Google sent back, exchanged for an ID token and that token checked. */
export async function googleClaims(code: string, verifier: string, redirectUri: string): Promise<JWTPayload> {
  const tokens = await client(redirectUri).validateAuthorizationCode(endpoints().token, code, verifier);
  return verifyIdToken(tokens.idToken(), process.env.GOOGLE_CLIENT_ID!);
}

/** The school email these claims prove, lower-cased, or null: Google must have verified it, it must end in the
 * school's domain, and the account must belong to the school's Google Workspace (`hd`). All three, every time. */
export function schoolEmail(claims: JWTPayload, domain: string): string | null {
  const email = typeof claims.email === "string" ? claims.email.trim().toLowerCase() : "";
  const school = domain.toLowerCase();
  if (claims.email_verified !== true) return null;
  if (!email.endsWith(`@${school}`)) return null;
  if (typeof claims.hd !== "string" || claims.hd.toLowerCase() !== school) return null;
  return email;
}
