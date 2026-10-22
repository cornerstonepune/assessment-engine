"use server";

import { redirect } from "next/navigation";
import { endSession } from "./auth";

export async function signOut(): Promise<void> {
  await endSession();
  redirect("/login");
}
