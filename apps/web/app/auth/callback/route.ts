import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { supabaseEnv } from "@/lib/supabase";

/**
 * Where a sign-in link lands.
 *
 * Supabase can hand the session back three ways, and only two of them reach a server:
 *   - `token_hash` + `type` — what our email template sends. Verified here. This is the one to keep.
 *   - `code` — the PKCE exchange, when the link was started by a browser client.
 *   - `#access_token=…` — a URL fragment, which browsers never send to the server. A link that
 *     arrives this way cannot be completed here at all; that was the original bug, and it read to
 *     the user as "that link has expired" on an otherwise healthy page.
 *
 * The session cookies are written onto the redirect response itself. Setting them on the request's
 * cookie store instead is the other classic way to lose a login: the exchange succeeds, nothing is
 * persisted, and the next page bounces straight back to sign-in.
 */
export async function GET(request: NextRequest) {
  const env = supabaseEnv();
  const params = request.nextUrl.searchParams;
  const tokenHash = params.get("token_hash");
  const type = params.get("type");
  const code = params.get("code");
  const next = params.get("next");
  const target = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";

  if (!env) return NextResponse.redirect(new URL("/login?error=config", request.url));
  if (!tokenHash && !code) {
    // Nothing in the query means the session is in the fragment, which only the browser can read.
    // The fragment survives this redirect, so /auth/finish picks it up there.
    return NextResponse.redirect(new URL("/auth/finish", request.url));
  }

  const response = NextResponse.redirect(new URL(target, request.url));
  const supabase = createServerClient(env.url, env.key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (list) => list.forEach(({ name, value, options }) => response.cookies.set(name, value, options)),
    },
  });

  const { error } = tokenHash
    ? await supabase.auth.verifyOtp({ type: (type as "magiclink") ?? "magiclink", token_hash: tokenHash })
    : await supabase.auth.exchangeCodeForSession(code!);

  if (error) {
    const to = new URL("/login", request.url);
    to.searchParams.set("error", "link");
    return NextResponse.redirect(to);
  }
  return response;
}
