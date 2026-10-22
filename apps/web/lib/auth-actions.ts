"use server";

import { revalidatePath } from "next/cache";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { CLASSES_COOKIE, endSession, requireStaff, signInFailed, signInRefused, startSession, SUBJECT_COOKIE, verifyStaff } from "./auth";

export async function signIn(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  if (email && (await signInRefused(email))) redirect("/login?error=wait");
  const staff = email && password ? await verifyStaff(email, password) : null;
  if (!staff) {
    if (email) await signInFailed(email);
    redirect("/login?error=denied");
  }
  await startSession(staff.email);
  // what waits on a person is the first page anyone sees (goals/ny1-needs-you.yaml)
  redirect("/today");
}

export async function signOut(): Promise<void> {
  await endSession();
  redirect("/login");
}

/** The class and the subject chosen in the bar at the top of every screen (goals/s1-subject-class-and-today.yaml): the
 *  person's own classes ("mine"), every class ("every"), or one class ("class:2B"); a subject by its code. A view kept in
 *  a cookie, never a permission: whichever is chosen, every class's page opens for every member of staff
 *  (goals/ux9c-one-role.yaml). */
export async function choose(formData: FormData): Promise<void> {
  await requireStaff();
  const jar = await cookies();
  const keep = { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/" } as const;
  const classes = String(formData.get("class") ?? "");
  if (classes === "every" || classes.startsWith("class:")) jar.set(CLASSES_COOKIE, classes, keep);
  else jar.delete(CLASSES_COOKIE);
  const subject = String(formData.get("subject") ?? "");
  if (subject) jar.set(SUBJECT_COOKIE, subject, keep);
  revalidatePath("/", "layout");
  // back to the page the bar was on, now showing what was chosen: only a path of this site is followed
  const from = (await headers()).get("referer");
  const path = from ? new URL(from).pathname + new URL(from).search : "/today";
  redirect(path.startsWith("/") && !path.startsWith("//") ? path : "/today");
}
