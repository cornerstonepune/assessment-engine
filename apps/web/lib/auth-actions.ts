"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { supabaseServer } from "./supabase";

export async function sendMagicLink(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) redirect("/login?error=email");
  const supabase = await supabaseServer();
  if (!supabase) redirect("/login?error=config");
  const origin = (await headers()).get("origin") ?? process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: `${origin}/auth/callback`, shouldCreateUser: true },
  });
  redirect(error ? "/login?error=send" : "/login?sent=1");
}

export async function signOut(): Promise<void> {
  const supabase = await supabaseServer();
  if (supabase) await supabase.auth.signOut();
  redirect("/login");
}
