"use server";

import { redirect } from "next/navigation";
import { endSession, startSession, verifyStaff } from "./auth";

export async function signIn(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const staff = email && password ? await verifyStaff(email, password) : null;
  if (!staff) redirect("/login?error=denied");
  await startSession(staff.email);
  redirect("/");
}

export async function signOut(): Promise<void> {
  await endSession();
  redirect("/login");
}
