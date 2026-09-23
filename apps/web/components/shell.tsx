import type { ReactNode } from "react";
import { Nav, type NavItem } from "./nav";
import { signOut } from "@/lib/auth-actions";
import type { Session } from "@/lib/auth";

// The menu is the teacher's week (BUILD-ORDER, "the website as the teacher's week"): what waits on them, the
// children, the papers coming back, the papers going out, what is taught, the questions it is taught with.
export const NAV: readonly NavItem[] = [
  { href: "/today", label: "Today", icon: "check", match: ["/today"] },
  { href: "/growth", label: "Children", icon: "growth", match: ["/growth"] },
  { href: "/capture", label: "Marking", icon: "camera", match: ["/capture"] },
  { href: "/worksheets", label: "Papers", icon: "sheet", match: ["/worksheets", "/home"] },
  { href: "/", label: "Curriculum", icon: "map", match: ["/", "/skill-sets"] },
  { href: "/library", label: "Question bank", icon: "bank", match: ["/library"] },
  { href: "/workflows", label: "How it works", icon: "flow", match: ["/workflows"] },
];

export function Shell({ me, children }: { me: Session; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <aside className="flex w-full flex-col bg-basalt px-[18px] py-[26px] text-lime md:w-[230px] md:shrink-0">
        <div className="mb-9 flex items-center gap-[10px]">
          <Mark />
          <div className="font-heading text-[19px] text-lime">cornerstone</div>
        </div>
        <Nav items={NAV} />
        <div className="mt-auto pt-8">
          <div className="label !text-bamboo opacity-75">Grade 1–4 · Maths</div>
          <div className="mt-3 flex items-center justify-between gap-2 text-[12.5px] text-bamboo">
            <span className="truncate" title={me.email}>{me.name}</span>
            {me.devBypass ? (
              <span className="pill pill-terracotta">dev bypass</span>
            ) : (
              <form action={signOut}>
                <button className="cursor-pointer text-bamboo underline-offset-2 hover:underline" type="submit">
                  Sign out
                </button>
              </form>
            )}
          </div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">{children}</main>
    </div>
  );
}

// The courtyard mark: the child at the centre, the ring, the door. One colour at a time.
function Mark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
      <path d="M2 2h22v22H16.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M9.5 24H2V2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="13" cy="12" r="3.6" fill="currentColor" />
    </svg>
  );
}

export function PageHeader({ stage, title, sub }: { stage: string; title: string; sub: string }) {
  return (
    <header className="border-b border-basalt/12 px-5 pt-6 pb-[18px] md:px-9">
      <div className="label mb-2 !text-monsoon !tracking-[0.08em]">{stage}</div>
      <h1 className="text-[26px] leading-tight">{title}</h1>
      <p className="mt-[6px] max-w-[620px] text-[13.5px] leading-[1.5] text-basalt/62">{sub}</p>
      <div className="chalkline" />
    </header>
  );
}

export function Body({ children }: { children: ReactNode }) {
  return <div className="flex-1 px-5 pt-[22px] pb-8 md:px-9">{children}</div>;
}

export function Panel({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="text-[16px]">{title}</h2>
        {aside ? <div className="fact text-[11px] text-basalt/55">{aside}</div> : null}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Pill({ tone, children }: { tone: "neem" | "bamboo" | "terracotta" | "monsoon"; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

// The material a state is drawn in. One place, because two screens now show the same states and a
// second copy is a second vocabulary.
export const TONE_BG = { neem: "bg-neem", bamboo: "bg-bamboo", terracotta: "bg-terracotta", monsoon: "bg-monsoon" } as const;
export const TONE_EDGE = { neem: "border-l-neem", bamboo: "border-l-bamboo", terracotta: "border-l-terracotta", monsoon: "border-l-monsoon" } as const;
export type Tone = keyof typeof TONE_BG;

export function Tile({ tone, n, words }: { tone: Tone; n: number; words: string }) {
  return (
    <div className={`panel border-l-4 p-3 ${TONE_EDGE[tone]}`}>
      <div className="font-heading text-[26px] leading-none">{n}</div>
      <div className="mt-2 text-[12.5px] text-basalt/62">{words}</div>
    </div>
  );
}

export function Bar({ tone, share, width }: { tone: Tone; share: number; width: number }) {
  return (
    <span className="inline-block h-[6px] bg-basalt/10" style={{ width }} aria-hidden="true">
      <span className={`block h-full ${TONE_BG[tone]}`} style={{ width: `${Math.round(share * 100)}%` }} />
    </span>
  );
}

export function Notice({ tone, children }: { tone: "neem" | "terracotta"; children: ReactNode }) {
  return (
    <p className={`mb-4 border p-3 text-[13.5px] ${tone === "neem" ? "border-neem/30 bg-neem/10" : "border-terracotta/30 bg-terracotta/10"}`} role="status">
      {children}
    </p>
  );
}

// Three signals, never two: blank, wrong, and wrong-with-working stay distinct (rule 5).
export function MarkPill({ status, working }: { status: string; working?: string }) {
  if (status === "correct") return <Pill tone="neem">right</Pill>;
  if (status === "blank") return <Pill tone="monsoon">blank</Pill>;
  if (status === "wrong") return <Pill tone="terracotta">{working ? "wrong · with working" : "wrong"}</Pill>;
  if (status === "unreadable") return <Pill tone="bamboo">could not read</Pill>;
  if (status === "needs_teacher") return <Pill tone="bamboo">for you to judge</Pill>;
  return <Pill tone="monsoon">{status}</Pill>;
}

// A section whose data does not exist yet says so, names what fills it, and shows the real count.
export function NotYet({ what, when, facts }: { what: string[]; when: string; facts: [string, number][] }) {
  return (
    <div className="grid gap-[18px] md:grid-cols-[1fr_300px]">
      <Panel title="What this screen will show">
        <ul className="grid gap-2 text-[14px]">
          {what.map((w) => (
            <li key={w} className="flex gap-3">
              <span className="mt-[9px] h-[2px] w-4 shrink-0 bg-basalt/25" />
              <span>{w}</span>
            </li>
          ))}
        </ul>
        <p className="note mt-4">{when}</p>
      </Panel>
      <Panel title="In the database today">
        <table className="grid">
          <tbody>
            {facts.map(([k, n]) => (
              <tr key={k}>
                <td className="fact">{k}</td>
                <td className="num">{n}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
