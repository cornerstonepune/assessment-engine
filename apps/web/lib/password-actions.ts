"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { after } from "next/server";
import { requireStaff, signInFailed, signInRefused, startSession, verifyStaff } from "./auth";
import { sendMail } from "./mail";
import { passwordProblem, setPassword } from "./password";
import { askedTooOften, emailFor, LINK_COOKIE, makeLink, recordAsk, sayMail, spend, tokenHash } from "./password-links";
import { staffList } from "./queries";

// Setting your own password: the three things a person does (goals/auth-email-password.yaml) — ask for a link when
// the password is forgotten, set a new one from the link, and change the one you have. The pages are under /login,
// which is the only part of the site a request with no session reaches (proxy.ts).

/** The site a link points at: its own name where Vercel says it (`NEXT_PUBLIC_SITE_URL`, docs/deploy.md), otherwise
 *  the address the request arrived on — a Host header is anyone's to send, and a link built from one could be made to
 *  point somewhere else and carry the token there. */
function from(head: Headers): string {
  const named = process.env.NEXT_PUBLIC_SITE_URL;
  if (named) return named.replace(/\/$/, "");
  const host = head.get("host") ?? "localhost";
  const proto = head.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${proto}://${host}`;
}

function address(head: Headers): string {
  return head.get("x-forwarded-for")?.split(",")[0]?.trim() || head.get("x-real-ip") || "unknown";
}

function words(site: string, token: string, purpose: "reset" | "first", minutes: string): string {
  const link = `${site}/login/link?token=${encodeURIComponent(token)}`;
  const why =
    purpose === "first"
      ? "You have been added to the Cornerstone assessment site as staff. Set your password here:"
      : "Someone asked to set a new password for your Cornerstone assessment account. Set it here:";
  return [
    why,
    "",
    link,
    "",
    `The link works once and runs out in ${minutes}.`,
    "If you did not ask for this, nothing has changed: ignore this email and tell the educator coordinator.",
    "",
    "Cornerstone assessment — staff only",
  ].join("\n");
}

/** Sends the link after the answer has gone back, so a staff email and an email nobody holds take the same time: the
 *  sending itself is what takes long enough to tell them apart. What became of it lands on the link's own row. */
function sendAfterAnswering(to: string, token: string, purpose: "reset" | "first", site: string, minutes: string) {
  const subject = purpose === "first" ? "Set your Cornerstone password" : "Set a new Cornerstone password";
  after(async () => {
    const mail = await sendMail(to, subject, words(site, token, purpose, minutes));
    await sayMail(tokenHash(token), mail);
  });
}

export async function askForLink(formData: FormData): Promise<void> {
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const head = await headers();
  if (email) {
    // the same statements whichever email was typed, and the sending itself left until after the answer
    const tooOften = await askedTooOften(email, address(head));
    await recordAsk(email, address(head));
    const known = (await staffList()).some((s) => s.email.toLowerCase() === email);
    if (known && !tooOften) {
      const token = await makeLink(email, "reset");
      sendAfterAnswering(email, token, "reset", from(head), "an hour");
    }
  }
  redirect("/login/forgot?sent=1");
}

/** The link emailed to a new member of staff, sent as the Staff page adds them. Every function a "use server" module
 *  exports is a door of its own, so this one checks who is asking even though the Staff page already has. */
export async function sendFirstLink(email: string): Promise<void> {
  await requireStaff();
  const head = await headers();
  const token = await makeLink(email, "first");
  sendAfterAnswering(email, token, "first", from(head), "seven days");
}

export async function setNewPassword(formData: FormData): Promise<void> {
  const jar = await cookies();
  const token = jar.get(LINK_COOKIE)?.value ?? "";
  const email = await emailFor(token);
  if (!email) redirect("/login/new-password?error=gone");
  const password = String(formData.get("password") ?? "");
  if (password !== String(formData.get("again") ?? "")) redirect("/login/new-password?error=match");
  const problem = await passwordProblem(password, email);
  if (problem) redirect(`/login/new-password?problem=${encodeURIComponent(problem)}`);
  await spend(token);
  // ends every session of theirs open anywhere, this link's own among them, before a new one is given out
  await setPassword(email, password);
  jar.delete(LINK_COOKIE);
  await startSession(email);
  redirect("/today");
}

export async function changeMyPassword(formData: FormData): Promise<void> {
  const me = await requireStaff();
  // the current password is guessed no more freely here than on the sign-in page: the same count, the same window
  if (await signInRefused(me.email)) redirect("/account/password?error=wait");
  const current = String(formData.get("current") ?? "");
  if (!(await verifyStaff(me.email, current))) {
    await signInFailed(me.email);
    redirect("/account/password?error=current");
  }
  const password = String(formData.get("password") ?? "");
  if (password !== String(formData.get("again") ?? "")) redirect("/account/password?error=match");
  const problem = await passwordProblem(password, me.email);
  if (problem) redirect(`/account/password?problem=${encodeURIComponent(problem)}`);
  await setPassword(me.email, password);
  // their other browsers are signed out; this one is given a cookie signed after the password, so it stays signed in
  await startSession(me.email);
  redirect("/account/password?saved=1");
}
