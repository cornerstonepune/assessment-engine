// Sign in with Google, step two: Google sends the person back with a code. The state must be the one this browser was
// given, the code is exchanged with its verifier, the ID token is checked, and only a verified school account of the
// school's own Workspace is let in. Someone new to the list joins it with the rule's role (goals/a1-sign-in-with-google.yaml).
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { GOOGLE_COOKIE, callbackUrl, startSession } from "@/lib/auth";
import { googleClaims, googleConfigured, schoolEmail } from "@/lib/google";
import { joinStaff, signInRule } from "@/lib/sign-in";

export async function GET(request: Request) {
  const rule = await signInRule();
  if (!googleConfigured() || !rule) redirect("/login?error=unconfigured");
  const jar = await cookies();
  const [state, verifier] = (jar.get(GOOGLE_COOKIE)?.value ?? "").split(".");
  jar.delete({ name: GOOGLE_COOKIE, path: "/login" });
  const q = new URL(request.url).searchParams;
  const code = q.get("code");
  if (!code || !state || !verifier || q.get("state") !== state) redirect("/login?error=failed");

  let email: string | null = null;
  let name = "";
  try {
    const claims = await googleClaims(code, verifier, callbackUrl(request));
    email = schoolEmail(claims, rule.domain);
    name = typeof claims.name === "string" && claims.name.trim() ? claims.name.trim() : "";
  } catch {
    // a refused exchange or a token that fails its checks: nothing about it is shown or logged
    redirect("/login?error=failed");
  }
  if (!email) redirect("/login?error=school");
  await joinStaff(email, name || email.split("@")[0], rule.new_staff_role);
  await startSession(email);
  // what waits on a person is the first page anyone sees (goals/ny1-needs-you.yaml)
  redirect("/today");
}
