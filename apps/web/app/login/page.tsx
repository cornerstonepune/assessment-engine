import { redirect } from "next/navigation";
import Link from "@/components/link";
import { currentStaff } from "@/lib/auth";
import { signIn } from "@/lib/auth-actions";
import { Logo } from "@/components/logo";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function LoginPage({ searchParams }: Props) {
  if (await currentStaff()) redirect("/");
  const q = await searchParams;

  return (
    <main className="mx-auto flex min-h-dvh max-w-[420px] flex-col justify-center px-5 py-10">
      <div className="mb-8 flex items-center gap-3 text-basalt">
        <Logo size={30} />
        <span className="font-heading text-[19px]">cornerstone</span>
        <span className="label ml-1">assessment</span>
      </div>
      <h1 className="text-[26px] leading-tight">Sign in</h1>
      <p className="mt-2 text-[13.5px] text-basalt/62">Staff only.</p>
      <div className="chalkline" />

      {q.error === "denied" ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          That email and password do not match a staff member.
        </p>
      ) : null}
      {q.error === "wait" ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          Too many wrong passwords for that email. Wait a few minutes, then try again.
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

      <p className="mt-6 text-[13.5px]">
        <Link href="/login/forgot" className="underline-offset-2 hover:underline">
          Forgot your password?
        </Link>
      </p>
    </main>
  );
}
