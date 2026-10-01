import { NextResponse, type NextRequest } from "next/server";
import { devBypass, SESSION_COOKIE, sessionEmail } from "./lib/session-cookie";

// Before any route renders, a request with no good staff session goes to sign-in, and an API route answers 401.
// The check is optimistic: the cookie's signature and expiry, never the staff list. Every page, route and action
// still calls requireStaff, which looks the person up. A layout's check alone let a page render into the RSC payload
// (Next 16's auth guide, "Layouts and auth checks"; goals/p0-every-page-checks-who-asks.yaml).
export function proxy(request: NextRequest) {
  if (devBypass()) return NextResponse.next();
  let email: string | null = null;
  try {
    email = sessionEmail(request.cookies.get(SESSION_COOKIE)?.value);
  } catch {
    // no AUTH_SECRET: nobody can be signed in, and the sign-in page says why
  }
  if (email) return NextResponse.next();
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Sign in first." }, { status: 401 });
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  // everything but the sign-in page and Next's own and public files; the API routes go through it too
  matcher: ["/((?!login|_next/static|_next/image|favicon.ico|.*\\.svg$).*)"],
};
