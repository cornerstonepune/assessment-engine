import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { deadline } from "./deadline";
import { staffList, type Staff } from "./queries";
import { devBypass, SESSION_COOKIE, SESSION_DAYS, sessionEmail, sessionValue } from "./session-cookie";

// Who is signed in.
/** What the bar at the top shows (`choose`, goals/s1-subject-class-and-today.yaml): `everyClass`, every class rather
 *  than the person's own (goals/ux9c-one-role.yaml); `oneClass`, one class alone; `subject`, the subject chosen, a code
 *  of `subject` (null: the first). A view, never a permission. */
export type Session = Staff & { devBypass: boolean; everyClass: boolean; oneClass: string | null; subject: string | null };
/** The cookie that keeps a person's choice of class: "every", or "class:" and one class; none is their own classes. */
export const CLASSES_COOKIE = "cs_classes";
/** The cookie that keeps the subject chosen at the top. */
export const SUBJECT_COOKIE = "cs_subject";

/** The class choice a cookie holds. */
export function classChoice(value: string | undefined): { everyClass: boolean; oneClass: string | null } {
  if (value === "every") return { everyClass: true, oneClass: null };
  return { everyClass: false, oneClass: value?.startsWith("class:") && value.length > 6 ? value.slice(6) : null };
}

// Google's short-lived state and PKCE verifier, between sending a person to Google and their coming back
// (app/login/google). Read under /login only.
export const GOOGLE_COOKIE = "cs_google";

/** Where Google sends a person back to: this site's own address, so production and a preview each name their own. */
export function callbackUrl(request: Request): string {
  return new URL("/login/google/callback", request.url).toString();
}

export async function startSession(email: string): Promise<void> {
  (await cookies()).set(SESSION_COOKIE, sessionValue(email), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_DAYS * 86_400,
  });
}

export async function endSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}

// Who is signed in, or null when the cookie is missing, edited, expired or names nobody on the
// staff list. A database that does not answer is NOT "signed out": it throws, and the person reads
// that the database did not answer (app/error.tsx). Swallowing it once sent a signed-in founder to
// the login page during an outage, which read as a broken password. Once per request, however many
// pages, layouts and data reads ask.
export const currentStaff = cache(async (): Promise<Session | null> => {
  if (devBypass()) return { email: "dev@local", name: "Dev bypass", role: "coordinator", classes: [], devBypass: true, everyClass: true, oneClass: null, subject: null };
  const jar = await cookies();
  const email = sessionEmail(jar.get(SESSION_COOKIE)?.value);
  if (!email) return null;
  const staff = (await deadline(staffList())).find((s) => s.email.toLowerCase() === email.toLowerCase());
  // named fields, never the record: an old password hash some rows still carry stays on the server
  return staff
    ? {
        email: staff.email,
        name: staff.name,
        role: staff.role,
        classes: staff.classes ?? [],
        devBypass: false,
        ...classChoice(jar.get(CLASSES_COOKIE)?.value),
        subject: jar.get(SUBJECT_COOKIE)?.value || null,
      }
    : null;
});

// For every page, route and server action: the signed-in staff member, or a redirect to /login. Each calls it
// itself; a layout's check alone is not enough (Next 16's auth guide, "Layouts and auth checks").
export async function requireStaff(): Promise<Session> {
  const me = await currentStaff();
  if (me) return me;
  redirect("/login");
}
