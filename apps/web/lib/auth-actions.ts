"use server";

import { revalidatePath } from "next/cache";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { CLASSES_COOKIE, endSession, requireStaff } from "./auth";

export async function signOut(): Promise<void> {
  await endSession();
  redirect("/login");
}

/** Every class, or the person's own first: one tap in the menu (goals/ux9c-one-role.yaml). A view kept in a cookie, never
 *  a permission: whichever is chosen, every class's page opens for every member of staff. */
export async function seeClasses(formData: FormData): Promise<void> {
  await requireStaff();
  const jar = await cookies();
  if (formData.get("classes") === "every") {
    jar.set(CLASSES_COOKIE, "every", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/" });
  } else {
    jar.delete(CLASSES_COOKIE);
  }
  revalidatePath("/", "layout");
  // back to the page the menu was on, now showing what was chosen: only a path of this site is followed
  const from = (await headers()).get("referer");
  const path = from ? new URL(from).pathname + new URL(from).search : "/today";
  redirect(path.startsWith("/") && !path.startsWith("//") ? path : "/today");
}
