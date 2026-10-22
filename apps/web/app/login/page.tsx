import { redirect } from "next/navigation";
import { currentStaff } from "@/lib/auth";
import { googleConfigured } from "@/lib/google";
import { signInRule } from "@/lib/sign-in";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function LoginPage({ searchParams }: Props) {
  if (await currentStaff()) redirect("/");
  const q = await searchParams;
  // without the Google secrets or the school's rule, no one can be let in: say so rather than offer a button that fails
  const ready = googleConfigured() && (await signInRule()) !== null;

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
      <p className="mt-2 text-[13.5px] text-basalt/62">Staff only, with your Cornerstone school Google account.</p>
      <div className="chalkline" />

      {q.error === "school" ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          Use your Cornerstone school Google account.
        </p>
      ) : null}
      {q.error === "failed" ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          Google did not finish signing you in. Try again.
        </p>
      ) : null}

      {ready ? (
        <a className="btn mt-6 text-center" href="/login/google">
          Sign in with Google
        </a>
      ) : (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          Sign-in isn&apos;t set up yet. Ask Nimish.
        </p>
      )}
    </main>
  );
}
