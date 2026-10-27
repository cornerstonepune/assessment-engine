import { cookies } from "next/headers";
import Link from "@/components/link";
import { Logo } from "@/components/logo";
import { emailFor, LINK_COOKIE } from "@/lib/password-links";
import { setNewPassword } from "@/lib/password-actions";
import { sql } from "@/lib/db";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// "Set a new password" — where an emailed link leads (goals/auth-email-password.yaml). The token itself is in a cookie
// this browser was given at /login/link, never in the address or on this page. A link that is used, replaced by a
// newer one, or out of time opens nothing, and says so plainly rather than hinting at whose it was.
export default async function NewPasswordPage({ searchParams }: Props) {
  const q = await searchParams;
  const token = (await cookies()).get(LINK_COOKIE)?.value ?? "";
  const email = q.error === "gone" ? null : await emailFor(token);
  const [row] = await sql<{ least: number }[]>`
    select (select value from threshold where key = 'password.min_length')::int as least`;

  return (
    <main className="mx-auto flex min-h-dvh max-w-[420px] flex-col justify-center px-5 py-10">
      <div className="mb-8 flex items-center gap-3 text-basalt">
        <Logo size={30} />
        <span className="font-heading text-[19px]">cornerstone</span>
        <span className="label ml-1">assessment</span>
      </div>
      <h1 className="text-[26px] leading-tight">Set a new password</h1>
      {email ? (
        <p className="mt-2 text-[13.5px] text-basalt/62">
          For {email}. At least {row?.least ?? 10} characters, and not your email address.
        </p>
      ) : (
        <p className="mt-2 text-[13.5px] text-basalt/62">Staff only.</p>
      )}
      <div className="chalkline" />

      {email ? (
        <>
          {q.error === "match" ? (
            <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
              The two passwords are not the same.
            </p>
          ) : null}
          {q.problem ? (
            <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
              {q.problem}
            </p>
          ) : null}
          <form action={setNewPassword} className="mt-6 grid gap-4">
            <label className="field">
              <span className="label">New password</span>
              <input className="input" type="password" name="password" autoComplete="new-password" required />
            </label>
            <label className="field">
              <span className="label">The same password again</span>
              <input className="input" type="password" name="again" autoComplete="new-password" required />
            </label>
            <button className="btn" type="submit">
              Save it and sign in
            </button>
          </form>
        </>
      ) : (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          That link no longer works. A link works once, runs out in an hour, and a newer one replaces it. Ask for a
          fresh one.
        </p>
      )}

      <p className="mt-6 text-[13.5px]">
        <Link href="/login/forgot" className="underline-offset-2 hover:underline">
          Send me another link
        </Link>
      </p>
    </main>
  );
}
