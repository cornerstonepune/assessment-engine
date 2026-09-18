"use client";

import { createBrowserClient } from "@supabase/ssr";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * The half of sign-in a server cannot do.
 *
 * Supabase's default email sends the session back in the URL fragment (`#access_token=…`), and a
 * browser never transmits a fragment to the server — so `/auth/callback` sees an empty query and
 * bounces here. The fragment survives that redirect, so this page can read it, hand the tokens to
 * the browser client, and let it write the same cookies the server reads.
 *
 * This exists because the project is on Supabase's built-in email sender, which does not allow a
 * custom template. With SMTP configured, the template can carry a `token_hash` instead, the server
 * route handles everything, and this page becomes dead weight worth deleting.
 */
export default function AuthFinishPage() {
  const router = useRouter();
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const access_token = hash.get("access_token");
    const refresh_token = hash.get("refresh_token");

    if (hash.get("error_description")) {
      setFailed(hash.get("error_description"));
      return;
    }
    if (!access_token || !refresh_token) {
      router.replace("/login?error=link");
      return;
    }

    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) {
      router.replace("/login?error=config");
      return;
    }

    createBrowserClient(url, key)
      .auth.setSession({ access_token, refresh_token })
      .then(({ error }) => {
        window.location.hash = "";
        router.replace(error ? "/login?error=link" : "/");
      })
      .catch(() => router.replace("/login?error=link"));
  }, [router]);

  return (
    <main className="mx-auto flex min-h-dvh max-w-[420px] flex-col justify-center px-5 py-10">
      <h1 className="text-[26px] leading-tight">{failed ? "That link did not work" : "Signing you in…"}</h1>
      <div className="chalkline" />
      <p className="mt-4 text-[13.5px] text-basalt/62">
        {failed ?? "One moment. If this page stays here, ask for a new link."}
      </p>
    </main>
  );
}
