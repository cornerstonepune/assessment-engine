// Sign in with Google, step one: send the person to Google with a fresh state and PKCE verifier, kept in a short-lived
// cookie only this site reads, for the callback to check (goals/a1-sign-in-with-google.yaml).
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { GOOGLE_COOKIE, callbackUrl } from "@/lib/auth";
import { googleConfigured, googleStart } from "@/lib/google";
import { signInRule } from "@/lib/sign-in";

export async function GET(request: Request) {
  const rule = await signInRule();
  if (!googleConfigured() || !rule) redirect("/login?error=unconfigured");
  const { url, state, verifier } = googleStart(callbackUrl(request), rule.domain);
  (await cookies()).set(GOOGLE_COOKIE, `${state}.${verifier}`, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production" && new URL(request.url).protocol === "https:",
    sameSite: "lax",
    path: "/login",
    maxAge: 600,
  });
  redirect(url.toString());
}
