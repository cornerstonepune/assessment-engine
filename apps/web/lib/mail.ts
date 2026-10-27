import nodemailer from "nodemailer";

// The one place an email leaves this site (ring C, CLAUDE.md: the only file that names an outside service, as
// `lib/engine.ts` is the only one that names the engine). Plain SMTP, from environment variables, so no mail provider
// is chosen here or anywhere in the repository: the school points these five at whatever sender it has.
//
// Nothing is logged. A reset link in a log is a breach, and a staff email in one breaks rule 6, so a failure is
// recorded as a word on the link's own row (`password_link.mail`) and counted by `engine live watch`; the reason
// never leaves this function.
const ENV = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"] as const;

/** What became of an email: the words `password_link.mail` holds. */
export type Sent = "sent" | "not configured" | "failed";

/** The sender's settings, or null when any of the five is missing — then nothing is sent and nobody is told a secret. */
function settings(): { host: string; port: number; user: string; password: string; from: string } | null {
  if (ENV.some((k) => !process.env[k])) return null;
  const port = Number(process.env.SMTP_PORT);
  if (!Number.isInteger(port) || port <= 0) return null;
  return {
    host: process.env.SMTP_HOST!,
    port,
    user: process.env.SMTP_USER!,
    password: process.env.SMTP_PASSWORD!,
    from: process.env.SMTP_FROM!,
  };
}

/** True when the five variables are set. The health line reads the rows, not this: a page cannot see Vercel's settings. */
export function mailConfigured(): boolean {
  return settings() !== null;
}

export async function sendMail(to: string, subject: string, text: string): Promise<Sent> {
  const s = settings();
  if (!s) return "not configured";
  try {
    // A sender that does not answer must not hold a request open (auth rule: time out every outbound call).
    const post = nodemailer.createTransport({
      host: s.host,
      port: s.port,
      secure: s.port === 465,
      auth: s.user ? { user: s.user, pass: s.password } : undefined,
      connectionTimeout: 10_000,
      greetingTimeout: 10_000,
      socketTimeout: 15_000,
      // A sender on this machine (a test's own) has no certificate; anything else must present a good one.
      ignoreTLS: ["127.0.0.1", "localhost"].includes(s.host),
    });
    await post.sendMail({ from: s.from, to, subject, text });
    return "sent";
  } catch {
    return "failed";
  }
}
