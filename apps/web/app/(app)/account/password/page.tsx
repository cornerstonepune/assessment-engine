import Link from "@/components/link";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { sql } from "@/lib/db";
import { changeMyPassword } from "@/lib/password-actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Change your own password (goals/auth-email-password.yaml). Reached from the account line at the top of every screen.
// The current password is asked for, so a browser left open cannot be used to lock its owner out; saving it signs
// every other browser of theirs out and keeps this one.
export default async function MyPasswordPage({ searchParams }: Props) {
  const me = await requireStaff();
  const q = await searchParams;
  const [row] = await sql<{ least: number }[]>`
    select (select value from threshold where key = 'password.min_length')::int as least`;
  const least = row?.least ?? 10;

  return (
    <PageShell
      stage="Account"
      title="Change password"
      purpose={`Your own password for ${me.email}. At least ${least} characters, and not your email address.`}
      action={
        <Link href="/today" className="btn">
          What needs doing →
        </Link>
      }
      next={{ href: "/today", label: "What needs doing" }}
    >
      {q.saved ? <Notice tone="neem">Your password is changed. Any other browser you left signed in is signed out.</Notice> : null}
      {q.error === "current" ? <Notice tone="terracotta">That is not your current password.</Notice> : null}
      {q.error === "match" ? <Notice tone="terracotta">The two new passwords are not the same.</Notice> : null}
      {q.error === "wait" ? (
        <Notice tone="terracotta">Too many wrong passwords. Wait a few minutes, then try again.</Notice>
      ) : null}
      {q.problem ? <Notice tone="terracotta">{q.problem}</Notice> : null}

      <form action={changeMyPassword} className="mt-2 grid max-w-[420px] gap-4">
        <label className="field">
          <span className="label">Your current password</span>
          <input className="input" type="password" name="current" autoComplete="current-password" required />
        </label>
        <label className="field">
          <span className="label">New password</span>
          <input className="input" type="password" name="password" autoComplete="new-password" required />
        </label>
        <label className="field">
          <span className="label">The same password again</span>
          <input className="input" type="password" name="again" autoComplete="new-password" required />
        </label>
        <button className="btn" type="submit">
          Save the new password
        </button>
      </form>
    </PageShell>
  );
}
