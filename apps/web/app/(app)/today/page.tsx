import type { ReactNode } from "react";
import Link from "@/components/link";
import { Body, PageHeader } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { waiting } from "@/lib/queries-today";

// Today — the teacher's inbox (goals/u1-today.yaml): everything waiting on a person, in the order of the week, each
// with its count and one click to act. The engine proposes; a teacher approves.
export default async function Today() {
  const me = await requireStaff();
  const w = await deadline(waiting(me.email));
  const packs = w.packs.reduce((n, p) => n + p.n, 0);

  return (
    <>
      <PageHeader stage="Today" title="Today" sub="Everything waiting on you, in the order of the week. Each opens where you act on it." />
      <Body>
        <div className="grid gap-[14px] md:grid-cols-2 xl:grid-cols-3">
          <Card
            title="Answers to check"
            n={w.answers}
            words="answers the engine was not sure of, each shown with the child's own writing"
            href="/capture/check"
            action="Check them"
          />
          <Card
            title="Papers to sign off"
            n={w.papers}
            words="papers read with answers no one has signed off; a child's graph grows once they are"
            href="/capture"
            action="Sign them off"
          />
          <Card
            title="Next papers to approve"
            n={w.nextPapers}
            words="children whose checked work shows a skill to work on, with no next paper approved this week"
            href="/growth"
            action="See the children"
          />
          <Card title="Class papers to approve" n={packs} words="papers the engine proposed for a class, waiting for you before they print">
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
          <Card
            title="Skills to approve"
            n={w.skills}
            words="skills whose words or levels changed and wait for one approval"
            href="/skill-sets/approve"
            action="Review and approve"
          />
        </div>
      </Body>
    </>
  );
}

function Card(props: { title: string; n: number; words: string; href?: string; action?: string; children?: ReactNode }) {
  const { title, n, words, href, action, children } = props;
  return (
    <section aria-label={title} className="panel flex flex-col gap-2 p-4">
      <h2 className="font-heading text-[17px]">{title}</h2>
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
