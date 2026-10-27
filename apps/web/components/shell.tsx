import type { ReactNode } from "react";
import Link from "next/link";
import { GroupNav, GroupTabs, MenuButton } from "./nav";
import { ReportLink, Search } from "./top-bar";
import { Logo } from "./logo";
import { signOut } from "@/lib/auth-actions";
import type { Session } from "@/lib/auth";
import { mayUse } from "@/lib/access";
import { GROUPS } from "@/lib/menu";

// The shell of every page (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026: "the menu is being shown on just the
// left side. I think we can use the whole space of the screen. The menu can be on the top, or it can be a small button
// with three lines that opens the menu." One slim bar: the mark, the four groups (lib/menu.ts), then the search
// and the menu button. A group's other pages are tabs under the
// bar. The groups carry one count, on the first: what waits (lib/todo.ts `waitingCount`). Nothing here names a subject.
export function Shell({ me, waiting, grades, children }: { me: Session; waiting: number; grades: string; children: ReactNode }) {
  const setup = mayUse(me, "setup");
  const groups = GROUPS.filter((g) => !g.setup || setup);
  const counts = { doing: waiting || undefined };
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="relative z-30 bg-basalt text-lime print:hidden">
        <div className="mx-auto flex min-h-14 w-full max-w-[1560px] items-center gap-3 px-4 py-1 md:gap-5 md:px-8">
          <Link href="/today" className="flex shrink-0 items-center gap-[10px] text-lime no-underline hover:text-lime" aria-label="cornerstone, home">
            <Logo size={28} />
            <span className="font-heading text-[19px] max-sm:hidden">cornerstone</span>
          </Link>
          <GroupNav groups={groups} counts={counts} />
          <div className="ml-auto flex min-w-0 items-center gap-2 md:gap-3">
            <ReportLink />
            <Search />
            <MenuButton counts={counts}>
              <Account me={me} grades={grades} />
            </MenuButton>
          </div>
        </div>
      </header>
      <GroupTabs />
      <main className="mx-auto flex w-full min-w-0 max-w-[1560px] flex-1 flex-col">{children}</main>
    </div>
  );
}

function Account({ me, grades }: { me: Session; grades: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-basalt/75">
      {/* the engineering map is the coordinator's: an educator's menu holds the school's work alone */}
      {mayUse(me, "the_map") ? (
        <Link href="/workflows" className="inline-flex min-h-11 items-center">
          How it works
        </Link>
      ) : null}
      <Link href="/guide" className="inline-flex min-h-11 items-center">
        Guide
      </Link>
      <span className="label">{grades}</span>
      <div role="group" aria-label="Signed in" className="ml-auto flex items-center gap-4">
        <span className="truncate" title={me.email}>
          {me.name} · {classesSaid(me)}
        </span>
        {me.devBypass ? (
          <span className="pill pill-terracotta">dev bypass</span>
        ) : (
          <Link href="/account/password" className="inline-flex min-h-11 items-center">
            Change password
          </Link>
        )}
        {me.devBypass ? null : (
          <form action={signOut}>
            <button className="min-h-11 cursor-pointer underline-offset-2 hover:underline" type="submit">
              Sign out
            </button>
          </form>
        )}
      </div>
    </div>
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
  return <div className="min-w-0 flex-1 px-5 pt-[22px] pb-8 md:px-9">{children}</div>;
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
