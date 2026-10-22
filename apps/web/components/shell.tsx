import type { ReactNode } from "react";
import { Nav, type NavItem } from "./nav";
import { TopBar } from "./top-bar";
import { signOut } from "@/lib/auth-actions";
import type { Session } from "@/lib/auth";
import { mayUse } from "@/lib/access";
import type { Choices } from "@/lib/choices";

// The menu is the school's order of work (goals/ui1-menu-and-today.yaml): what waits today, what is taught, the
// assessments made from it, and the children they tell about. Each tab carries the count of what waits in it, from the
// list Today shows (lib/needs-you.ts). A child's own paper (CS + six hex) is an assessment; a library worksheet is
// curriculum. Papers, marking and making a paper are one tab (goals/u9-papers.yaml); its address stays /papers.
export const NAV: readonly NavItem[] = [
  { href: "/today", label: "Today", icon: "check", match: ["/today"] },
  { href: "/", label: "Curriculum", icon: "map", match: ["/", "/skill-sets", "/library", "/worksheets", "/asks"] },
  { href: "/papers", label: "Assessments", icon: "sheet", match: ["/papers", "/capture", "/make", "/home", "/worksheets/CS"] },
  { href: "/growth", label: "Children", icon: "growth", match: ["/growth"] },
];

export function Shell({ me, waiting, grades, choices, children }: { me: Session; waiting: Partial<Record<string, number>>; grades: string; choices: Choices; children: ReactNode }) {
  const subject = choices.subjects.find((x) => x.code === me.subject) ?? choices.subjects[0];
  const chosen = me.oneClass ? `class:${me.oneClass}` : me.everyClass || !me.classes?.length ? "every" : "mine";
  // On a phone the menu is one row of big tabs at the foot of the screen, so the bar and a page's heading are both at
  // the top (goals/ux7-phone-and-words.yaml: the heading in the top 120 px; goals/s1-subject-class-and-today.yaml); who
  // is signed in moves to the foot of the page there, as it is the menu's foot on a wider screen.
  return (
    <div className="flex min-h-dvh flex-col pb-[56px] md:flex-row md:pb-0 print:pb-0">
      <aside className="fixed inset-x-0 bottom-0 z-30 flex w-full flex-row items-center gap-2 bg-basalt px-3 py-[2px] text-lime md:static md:w-[230px] md:shrink-0 md:flex-col md:items-stretch md:gap-0 md:px-[18px] md:py-[26px] print:hidden">
        <div className="hidden items-center gap-[10px] md:mb-9 md:flex">
          <Mark />
          <div className="font-heading text-[19px] text-lime">cornerstone</div>
        </div>
        <Nav items={NAV.map((it) => ({ ...it, count: waiting[it.label] }))} />
        <Account me={me} grades={grades} subject={subject?.label ?? ""} className="mt-auto hidden pt-8 md:block" />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar choices={choices} subject={subject?.code ?? ""} chosen={chosen} own={me.classes ?? []} />
        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      </div>
      <footer className="bg-basalt px-5 py-4 md:hidden print:hidden">
        <Account me={me} grades={grades} subject={subject?.label ?? ""} />
      </footer>
    </div>
  );
}

function Account({ me, grades, subject, className }: { me: Session; grades: string; subject: string; className?: string }) {
  return (
    <div className={className}>
      {/* the engineering map is the coordinator's: an educator's menu holds the school's work alone */}
      {mayUse(me, "the_map") ? (
        <a href="/workflows" className="mb-4 block text-[12.5px] text-bamboo underline-offset-2 hover:underline">
          How it works
        </a>
      ) : null}
      <div className="label !text-bamboo opacity-75">{grades} · {subject}</div>
      <div role="group" aria-label="Signed in" className="mt-3 text-[12.5px] text-bamboo">
        <div className="flex items-center justify-between gap-2">
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
        {/* what the site opens on for this person (ADR 0073): never a guess; every class one choice away in the bar at the top
            (goals/s1-subject-class-and-today.yaml) */}
        <div className="mt-1 opacity-75">{classesSaid(me)}</div>
      </div>
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
    <header className="border-b border-basalt/12 px-5 pt-3 pb-[18px] md:px-9 md:pt-6">
      <div className="label mb-1 truncate !text-monsoon !tracking-[0.08em] md:mb-2 md:whitespace-normal" data-testid="stage">
        {stage}
      </div>
      <h1 className="text-[22px] leading-tight md:text-[26px]">{title}</h1>
      <p className="mt-[6px] max-w-[620px] text-[13.5px] leading-[1.5] text-basalt/62">{sub}</p>
      <div className="chalkline" />
    </header>
  );
}

export function Body({ children }: { children: ReactNode }) {
  return <div className="flex-1 px-5 pt-[22px] pb-8 md:px-9">{children}</div>;
}

// `label` names the panel as a region for a screen reader (and a test); `id` makes it a link target. The panel is
// the grid item itself — never wrap it to name it: a wrapper loses `.panel`'s min-width and a wide table then
// pushes a phone's page sideways.
export function Panel({ title, aside, label, id, children }: { title: string; aside?: ReactNode; label?: string; id?: string; children: ReactNode }) {
  return (
    <section className={`panel${id ? " scroll-mt-6" : ""}`} aria-label={label} id={id}>
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

/** The classes a person teaches, as the menu says them: the coordinator's are every class. */
export function classesSaid(me: Pick<Session, "role" | "classes">): string {
  if (me.role === "coordinator") return "Every class";
  return me.classes?.length ? `Teaches ${me.classes.join(", ")}` : "No class yet";
}
