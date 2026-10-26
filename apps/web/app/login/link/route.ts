import { NextResponse } from "next/server";
import { emailFor, LINK_COOKIE, LINK_COOKIE_MINUTES } from "@/lib/password-links";

// Where an emailed link lands. The token is moved out of the address and into a cookie of this browser's, then the
// person is sent to the page with nothing in the address: the token is in no history, no bookmark and no further log
// line (goals/auth-email-password.yaml). The link is NOT spent here — a mail scanner opening it must not burn it;
// it is spent when the password is actually set.
export async function GET(request: Request): Promise<NextResponse> {
  const token = new URL(request.url).searchParams.get("token") ?? "";
  const good = Boolean(await emailFor(token));
  const to = new URL(good ? "/login/new-password" : "/login/new-password?error=gone", request.url);
  const answer = NextResponse.redirect(to);
  if (good) {
    answer.cookies.set(LINK_COOKIE, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: LINK_COOKIE_MINUTES * 60,
    });
  }
  return answer;
}
