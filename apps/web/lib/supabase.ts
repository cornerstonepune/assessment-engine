import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export function supabaseEnv(): { url: string; key: string } | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return url && key ? { url, key } : null;
}

// Server-side Supabase client bound to the request's cookies. Only auth goes through it;
// data is read straight from Postgres (lib/db.ts).
export async function supabaseServer() {
  const env = supabaseEnv();
  if (!env) return null;
  const store = await cookies();
  return createServerClient(env.url, env.key, {
    cookies: {
      getAll: () => store.getAll(),
      setAll: (list) => {
        try {
          list.forEach(({ name, value, options }) => store.set(name, value, options));
        } catch {
          // Server components may not set cookies; the proxy refreshes the session instead.
        }
      },
    },
  });
}
