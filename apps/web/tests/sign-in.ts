// A member of staff signed in for a test: the session cookie, signed exactly as lib/session-cookie.ts signs one with
// the run's own secret. How a session starts (Google, goals/a1-sign-in-with-google.yaml) is tested once, in
// p5-sign-in-with-google.spec.ts; every other spec starts from a session, as a person does once signed in.
import { createHmac } from "node:crypto";
import type { Page } from "@playwright/test";

export function staffCookie(email: string) {
  const expiry = String(Date.now() + 86_400_000);
  const body = `${Buffer.from(email).toString("base64url")}.${expiry}`;
  const mac = createHmac("sha256", process.env.E2E_AUTH_SECRET!).update(body).digest("hex");
  return {
    name: "cs_staff",
    value: `${body}.${mac}`,
    domain: "localhost",
    path: "/",
    expires: Math.floor(Number(expiry) / 1000),
    httpOnly: true,
    secure: false,
    sameSite: "Lax" as const,
  };
}

/** Signs this page's browser in as `email` and opens Today, the first page anyone sees. */
export async function signIn(page: Page, email: string): Promise<void> {
  await page.context().addCookies([staffCookie(email)]);
  await page.goto("/today");
}
