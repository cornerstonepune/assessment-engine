import { NextResponse, type NextRequest } from "next/server";
import { supabaseServer } from "@/lib/supabase";

// The magic link lands here with a code; exchange it for a session and go to the app.
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const supabase = await supabaseServer();
  if (code && supabase) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.redirect(new URL("/login?error=link", request.url));
}
