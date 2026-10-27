// The one place this site talks to GitHub (ring C, CLAUDE.md: the only file that names an outside service, as
// lib/mail.ts is for email). A note from staff becomes an issue here, and their reports read back the issues' state
// (goals/feed_report_from_the_tool.yaml). The plain REST API with fetch: one call makes an issue, one reads them all, so
// no client library and no ticketing product.
//
// The token is GITHUB_FEEDBACK_TOKEN, set in Vercel: a fine-grained token for this repository with Issues: read and
// write, nothing else. It is never logged, never sent anywhere but GitHub, and never said: a failure is a word on the
// note's own row (`staff_note.status`), counted by `engine live watch`.

export const REPO = "cornerstonepune/assessment-engine";
/** Every issue made from the tool carries this label beside its kind's. */
export const FROM_THE_TOOL = "from-the-tool";

// A test points this at a GitHub of its own (tests/github-server.ts); nothing else sets it.
const API = () => (process.env.GITHUB_API_URL ?? "https://api.github.com").replace(/\/$/, "");
// GitHub that does not answer must not hold a request open (auth rule: time out every outbound call).
const WAIT_MS = 10_000;

/** What became of an issue: its number, or why there is none. */
export type Made = { number: number } | "not connected" | "failed";

function token(): string | null {
  return process.env.GITHUB_FEEDBACK_TOKEN || null;
}

/** True when the token is set. The health line reads the rows, not this: the engine cannot see Vercel's settings. */
export function githubConnected(): boolean {
  return token() !== null;
}

function headers(t: string): Record<string, string> {
  return {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${t}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
  };
}

export async function createIssue(title: string, body: string, labels: string[]): Promise<Made> {
  const t = token();
  if (!t) return "not connected";
  try {
    const res = await fetch(`${API()}/repos/${REPO}/issues`, {
      method: "POST",
      headers: headers(t),
      body: JSON.stringify({ title, body, labels }),
      signal: AbortSignal.timeout(WAIT_MS),
    });
    if (res.status !== 201) return "failed";
    const made = (await res.json()) as { number?: unknown };
    return typeof made.number === "number" ? { number: made.number } : "failed";
  } catch {
    return "failed";
  }
}

export type IssueState = { closed: boolean; labels: string[] };

/** The state of every issue made from the tool, by number; empty when GitHub is not connected or does not answer. One
 *  call: a page of a hundred, newest first, which is more than any one person's reports the page shows. */
export async function toolIssues(): Promise<Map<number, IssueState>> {
  const t = token();
  const out = new Map<number, IssueState>();
  if (!t) return out;
  try {
    const res = await fetch(`${API()}/repos/${REPO}/issues?labels=${FROM_THE_TOOL}&state=all&per_page=100`, {
      headers: headers(t),
      signal: AbortSignal.timeout(WAIT_MS / 2),
      cache: "no-store",
    });
    if (!res.ok) return out;
    for (const i of (await res.json()) as { number: number; state: string; labels: ({ name: string } | string)[] }[]) {
      out.set(i.number, { closed: i.state === "closed", labels: i.labels.map((l) => (typeof l === "string" ? l : l.name)) });
    }
  } catch {
    // nothing known: the page says "received", which is true
  }
  return out;
}
