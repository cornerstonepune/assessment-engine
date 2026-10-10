import type { ReactNode } from "react";
import Link from "@/components/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { staffList } from "@/lib/queries";
import { decides, ROLE_WORDS } from "@/lib/queries-people";
import { waiting } from "@/lib/queries-today";

// Today — everything waiting on a person, and who it is for (goals/u1-today.yaml, goals/ny1-needs-you.yaml): each with
// its count and one click to act, the signed-in person's first. Whose each kind is, is a row (`people.decides`, by the
// staff list's roles), so a school moves a decision to another person without code. The engine proposes; a person
// approves.
export default async function Today() {
  const me = await requireStaff();
  const [w, rows, staff] = await deadline(Promise.all([waiting(me.email), decides(), staffList()]));
  const packs = w.packs.reduce((n, p) => n + p.n, 0);
  const who = (roles: string[]) => {
    if (roles.includes(me.role)) return "For you";
    const names = staff.filter((s) => roles.includes(s.role)).map((s) => s.name);
    return names.length ? `For ${names.join(", ")}` : `No one on the staff list is ${roles.map((r) => ROLE_WORDS[r] ?? r).join(" or ")} yet`;
  };

  const cards: { roles: string[]; card: ReactNode }[] = [
    {
      roles: rows.answers ?? [],
      card: <Card key="answers" title="Answers to check" n={w.answers} who={who(rows.answers ?? [])} words="answers the engine was not sure of, each shown with the child's own writing" href="/capture/check" action="Check them" />,
    },
    {
      roles: rows.papers ?? [],
      card: <Card key="papers" title="Papers to sign off" n={w.papers} who={who(rows.papers ?? [])} words="papers read with answers no one has signed off; a child's graph grows once they are" href="/capture" action="Sign them off" />,
    },
    {
      roles: rows.home_papers ?? [],
      card: (
        <Card key="home" title="Home assessments to approve" n={w.nextPapers} who={who(rows.home_papers ?? [])} words="children whose checked work gives the engine a home assessment to propose, not yet approved this week" href="/make" action="Approve them" />
      ),
    },
    {
      roles: rows.class_papers ?? [],
      card: (
        <Card key="class" title="Class papers to approve" n={packs} who={who(rows.class_papers ?? [])} words="papers the engine proposed for a class, waiting for a person before they print">
          <ul className="grid gap-1 text-[13.5px]">
            {w.packs.map((p) => (
              <li key={`${p.section}|${p.week}|${p.kind}`}>
                <Link href={`/worksheets?section=${encodeURIComponent(p.section)}&week=${encodeURIComponent(p.week)}&kind=${p.kind}`}>
                  {p.section} · {p.week} · {p.kind}
                </Link>{" "}
                <span className="text-basalt/62">— {p.n} {p.n === 1 ? "paper" : "papers"}</span>
              </li>
            ))}
          </ul>
        </Card>
      ),
    },
    {
      roles: rows.skills ?? [],
      card: <Card key="skills" title="Skills to approve" n={w.skills} who={who(rows.skills ?? [])} words="skills whose words or levels the engine wrote or changed, each waiting for one approval — taught or not yet" href="/skill-sets/approve" action="Review and approve" />,
    },
    {
      roles: rows.topics ?? [],
      card: <Card key="topics" title="Topics not taught yet" n={w.topics} who={who(rows.topics ?? [])} words="topics whose skills are on no page and no child's paper until a person switches them on" href="/#not-taught" action="Switch them on" />,
    },
    ...w.asks.map((a) => ({
      roles: [a.for_role],
      card: <Card key={`asks-${a.for_role}`} title={`Questions for ${ROLE_WORDS[a.for_role] ?? a.for_role}`} n={a.n} who={who([a.for_role])} words="what the engine drafted and wants a person to agree with or correct: the taxonomy, its assumptions, each slice's decisions" href="/asks" action="Answer them" />,
    })),
  ];
  const mine = cards.filter((c) => c.roles.includes(me.role));
  const others = cards.filter((c) => !c.roles.includes(me.role));

  return (
    <>
      <PageHeader stage="Today" title="Today" sub="What waits on a person, and who it is for, yours first. Each opens where it is done." />
      <Body>
        <Part title="For you">{mine.map((c) => c.card)}</Part>
        <Part title="For others">{others.map((c) => c.card)}</Part>
      </Body>
    </>
  );
}

function Part({ title, children }: { title: string; children: ReactNode[] }) {
  return (
    <section aria-label={title} className="mb-6">
      <h2 className="label mb-2">{title}</h2>
      {children.length ? <div className="grid gap-[14px] md:grid-cols-2 xl:grid-cols-3">{children}</div> : <p className="note">Nothing here.</p>}
    </section>
  );
}

function Card(props: { title: string; n: number; who: string; words: string; href?: string; action?: string; children?: ReactNode }) {
  const { title, n, who, words, href, action, children } = props;
  return (
    <section aria-label={title} className="panel flex flex-col gap-2 p-4">
      <h3 className="font-heading text-[17px]">{title}</h3>
      <p className="label">{who}</p>
      {n === 0 ? (
        <p className="note">Nothing waiting</p>
      ) : (
        <>
          <span data-testid="count" className="font-heading text-[30px] leading-none">
            {n.toLocaleString("en-IN")}
          </span>
          <p className="text-[13px] text-basalt/70">{words}</p>
          {children}
          {href && action ? (
            <Link href={href} className="btn mt-1 self-start">
              {action}
            </Link>
          ) : null}
        </>
      )}
    </section>
  );
}
