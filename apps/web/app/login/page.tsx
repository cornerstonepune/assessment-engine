import { redirect } from "next/navigation";
import { currentStaff } from "@/lib/auth";
import { signIn } from "@/lib/auth-actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function LoginPage({ searchParams }: Props) {
  if (await currentStaff()) redirect("/");
  const q = await searchParams;

  return (
    <main className="mx-auto flex min-h-dvh max-w-[420px] flex-col justify-center px-5 py-10">
      <div className="mb-8 flex items-center gap-3 text-basalt">
        <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
          <path d="M2 2h22v22H16.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M9.5 24H2V2" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <circle cx="13" cy="12" r="3.6" fill="currentColor" />
        </svg>
        <span className="font-heading text-[19px]">cornerstone</span>
        <span className="label ml-1">assessment</span>
      </div>
      <h1 className="text-[26px] leading-tight">Sign in</h1>
      <p className="mt-2 text-[13.5px] text-basalt/62">Staff only. Ask Nimish for a password.</p>
      <div className="chalkline" />

      {q.error === "denied" ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          That email and password do not match a staff member.
        </p>
      ) : null}

      <form action={signIn} className="mt-6 grid gap-4">
        <label className="field">
          <span className="label">School email</span>
          <input className="input" type="email" name="email" autoComplete="username" required />
        </label>
        <label className="field">
          <span className="label">Password</span>
          <input className="input" type="password" name="password" autoComplete="current-password" required />
        </label>
        <button className="btn" type="submit">
          Sign in
        </button>
      </form>
    </main>
  );
}
