// What a note from staff may hold, and how it is written into a GitHub issue (goals/feed_report_from_the_tool.yaml). No
// database and no network, so every rule here is tested on its own (tests/u70-feedback-rules.spec.ts).
//
// The repository is public, so the issue holds the person's words, the page with its ids taken out, their role and
// classes, a short name for their browser and the time: never a name, an email, a phone number or an id. A phone number
// and an email have a shape and are refused; a name has none, so the warning under the boxes is what guards against one.

export const KINDS = {
  bug: { words: "Something is broken", label: "bug" },
  feature: { words: "I would like something new", label: "feature" },
  question: { words: "A question", label: "question" },
} as const;
export type NoteKind = keyof typeof KINDS;

export const HOW_OFTEN = ["once", "sometimes", "every time"] as const;
export type HowOften = (typeof HOW_OFTEN)[number];

export const REFUSED_WORDS = "That looks like a name or a phone number; please take it out";
export const WARNING =
  "Please do not type a child's name, a parent's name or a phone number here. Use the class and roll number instead.";

export const TITLE_MAX = 80;

// Ten digits or more, spaces, dots, dashes or brackets between them allowed: an Indian mobile is ten, with +91 twelve.
const PHONE = /(?:\+?\d[\s().-]{0,2}){10,}/;
const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]{2,}/;

/** The kind words when the text holds a phone-number-shaped or email-shaped string, else null. */
export function refusal(...texts: string[]): string | null {
  return texts.some((t) => PHONE.test(t) || EMAIL.test(t)) ? REFUSED_WORDS : null;
}

// A zero-width space after `@` and `#` stops GitHub reading a mention (`@team`) or a link to an issue (`#12`), and
// the reader sees the same text.
const ZW = "​";
export function neutralise(text: string): string {
  return text.replace(/[@#]/g, (c) => c + ZW);
}

/** The person's words as GitHub shows them: in a fenced block, so nothing in them is read as markdown, HTML or a link;
 *  the fence is longer than any run of tildes in the text, so the words cannot close it. */
export function fenced(text: string): string {
  const longest = Math.max(0, ...(text.match(/~+/g) ?? []).map((r) => r.length));
  const fence = "~".repeat(Math.max(3, longest + 1));
  return `${fence}text\n${neutralise(text)}\n${fence}`;
}

/** The page's path with no query and no id: any part with a digit in it ("/growth/3f2a…", "/worksheets/CS0A1B2C") is
 *  written `[id]`. A path that is not this site's own is `/`. */
export function routeOnly(path: string): string {
  const p = (path || "/").split(/[?#]/)[0];
  if (!p.startsWith("/") || p.startsWith("//")) return "/";
  const parts = p.split("/").filter(Boolean).map((s) => (/\d/.test(s) || s.length > 40 ? "[id]" : s));
  return `/${parts.join("/")}`.slice(0, 200);
}

/** The browser and system, short: "Chrome 130 on Windows". Never the whole user agent. */
export function browserOf(ua: string): string {
  const b =
    ua.match(/(Edg|OPR|Firefox|Chrome|CriOS|FxiOS)\/(\d+)/) ??
    (/Safari\//.test(ua) ? ua.match(/(Version)\/(\d+)/) : null);
  const name = b ? ({ Edg: "Edge", OPR: "Opera", CriOS: "Chrome", FxiOS: "Firefox", Version: "Safari" } as Record<string, string>)[b[1]] ?? b[1] : "a browser";
  const os = /Android/.test(ua)
    ? "Android"
    : /iPhone|iPad/.test(ua)
      ? "iOS"
      : /Windows/.test(ua)
        ? "Windows"
        : /Mac OS X/.test(ua)
          ? "macOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "another system";
  return b ? `${name} ${b[2]} on ${os}` : `${name} on ${os}`;
}

/** "a coordinator", "an educator of 3A, 3B": the role and classes, never who. */
export function reportedBy(role: string, classes: string): string {
  const r = (role || "member of staff").toLowerCase();
  const a = /^[aeiou]/.test(r) ? "an" : "a";
  return classes ? `${a} ${r} of ${classes}` : `${a} ${r}`;
}

export type Note = {
  kind: NoteKind;
  doing: string;
  happened: string;
  howOften: HowOften | null;
  route: string;
  role: string;
  classes: string;
  browser: string;
  at: Date;
};

/** The first line of the person's words, trimmed to TITLE_MAX characters. */
export function issueTitle(n: Pick<Note, "doing" | "happened" | "kind">): string {
  const first = [n.happened, n.doing].map((t) => t.split("\n").map((l) => l.trim()).find(Boolean)).find(Boolean);
  const line = (first ?? KINDS[n.kind].words).replace(/\s+/g, " ");
  const cut = line.length > TITLE_MAX ? `${line.slice(0, TITLE_MAX - 1).trimEnd()}…` : line;
  return neutralise(cut);
}

/** When, as the school says a time: 27-Oct-2026 14:05 IST. */
export function whenSaid(at: Date): string {
  const f = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(at);
  const v = (t: string) => f.find((p) => p.type === t)?.value ?? "";
  return `${v("day")}-${v("month")}-${v("year")} ${v("hour")}:${v("minute")} IST`;
}

/** The issue's body, headed as .github/ISSUE_TEMPLATE/from-the-tool.yml heads a hand-made one. Only the person's two
 *  boxes are their words; every other line is chosen by the system from a fixed list or a fixed shape. */
export function issueBody(n: Note): string {
  return [
    "### What kind?",
    KINDS[n.kind].words,
    "### What were you doing?",
    fenced(n.doing),
    "### What did you expect, and what happened?",
    fenced(n.happened),
    ...(n.kind === "bug" ? ["### How often?", n.howOften ?? "not said"] : []),
    "### Page",
    `\`${routeOnly(n.route)}\``,
    "### Reported by",
    neutralise(reportedBy(n.role, n.classes)),
    "### Browser",
    neutralise(n.browser),
    "### When",
    whenSaid(n.at),
    "",
    "_Made by the Report a problem form of the assessment site._",
  ].join("\n\n");
}

/** What a person sees of their report: received until GitHub says more, taken up once Nimish adds `scope-locked`
 *  (the label that says it will be built), done once the issue is closed. */
export type Seen = "received" | "takenUp" | "done";
export function seenAs(issue: { closed: boolean; labels: string[] } | undefined): Seen {
  if (!issue) return "received";
  if (issue.closed) return "done";
  return issue.labels.includes("scope-locked") ? "takenUp" : "received";
}
