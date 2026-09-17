import { redirect } from "next/navigation";
import { staffList, type Staff } from "./queries";
import { supabaseServer } from "./supabase";

export type Session = Staff & { devBypass: boolean };

// True only in development and only when asked for. Production never bypasses (auth rule: a
// disabled gate is a ship blocker).
export function devBypass(): boolean {
  return process.env.NODE_ENV === "development" && process.env.AUTH_DEV_BYPASS === "1";
}

// Who is signed in, or null. Never throws.
export async function currentStaff(): Promise<Session | null> {
  if (devBypass()) return { email: "dev@local", name: "Dev bypass", role: "coordinator", devBypass: true };
  const supabase = await supabaseServer();
  if (!supabase) return null;
  const { data } = await supabase.auth.getUser();
  const email = data.user?.email?.toLowerCase();
  if (!email) return null;
  const staff = (await staffList()).find((s) => s.email.toLowerCase() === email);
  return staff ? { ...staff, devBypass: false } : null;
}

// For pages and server actions: the signed-in staff member, or a redirect to /login.
export async function requireStaff(): Promise<Session> {
  const me = await currentStaff();
  if (me) return me;
  const supabase = await supabaseServer();
  const signedInButNotStaff = supabase ? (await supabase.auth.getUser()).data.user != null : false;
  redirect(signedInButNotStaff ? "/login?denied=1" : "/login");
}
