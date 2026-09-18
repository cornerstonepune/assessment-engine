import { redirect } from "next/navigation";
import { currentStaff } from "@/lib/auth";
import { sendMagicLink } from "@/lib/auth-actions";
import { supabaseEnv } from "@/lib/supabase";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function LoginPage({ searchParams }: Props) {
  if (await currentStaff()) redirect("/");
  const q = await searchParams;
  const configured = supabaseEnv() !== null;

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
      <p className="mt-2 text-[13.5px] text-basalt/62">A link comes to your school email. No password.</p>
      <div className="chalkline" />

      {q.sent ? (
        <p className="mt-6 border border-neem/30 bg-neem/10 p-3 text-[13.5px]" role="status">
          Sent. Open the link on this device.
        </p>
      ) : null}
      {q.denied ? (
        <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
          That email is signed in but is not on the staff list. Ask Nimish to add it.
        </p>
      ) : null}
      {q.error === "email" ? <Err>That does not look like an email address.</Err> : null}
      {q.error === "send" ? <Err>The link could not be sent. Try again in a minute.</Err> : null}
      {q.error === "link" ? <Err>That link has expired or was already used. Ask for a new one.</Err> : null}
      {q.error === "fragment" ? (
        <Err>
          That link came back in a form this site cannot read. Ask for a new one — if it happens again, the sign-in email
          template needs to point at /auth/callback with a token_hash.
        </Err>
      ) : null}
      {q.error === "config" || !configured ? (
        <Err>
          Sign-in is not configured on this machine yet: add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to
          apps/web/.env.local (see env.example).
        </Err>
      ) : null}

      <form action={sendMagicLink} className="mt-6 grid gap-4">
        <label className="field">
          <span className="label">School email</span>
          <input className="input" type="email" name="email" autoComplete="email" required disabled={!configured} />
        </label>
        <button className="btn" type="submit" disabled={!configured}>
          Send me a link
        </button>
      </form>
    </main>
  );
}

function Err({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-6 border border-terracotta/30 bg-terracotta/10 p-3 text-[13.5px]" role="alert">
      {children}
    </p>
  );
}
