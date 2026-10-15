import type { ReactNode } from "react";
import Link from "@/components/link";
import { Panel } from "@/components/shell";

/** `none`: no answer at all on the skill yet, as against too few to say. */
export type Check = { key: string; skill: string; who: ReactNode; level: string; n: number; href: string; none?: boolean };

// Where the colours cannot say yet — grey, or no answer at all — the check that would place the child
// (goals/u11-colours-said.yaml). Nimish, 2026-09-30: "for areas where we don't have sufficient data points … we should
// have a clear recommendation around the next set of assessments … so that we know where the child is". Each check
// opens in the maker, its children, skill, level and size already chosen; nothing prints until an educator makes it.
// One line a check, its button on screen at any width (goals/ux4-class-and-child.yaml): the skills nobody has answered
// yet, often most of a grade early in the year, are folded under one line that says how many — `unanswered` says who.
export function ChecksPanel({ title, checks, unanswered }: { title: string; checks: Check[]; unanswered: string }) {
  if (!checks.length) return null;
  const some = checks.filter((c) => !c.none);
  const none = checks.filter((c) => c.none);
  return (
    <Panel title={title} label={title} aside={`${checks.length} ${checks.length === 1 ? "skill" : "skills"}`}>
      <p className="note mb-3">
        A skill is grey until it has enough checked answers to say. One short class assessment on it — at the grade&rsquo;s starting
        level, different questions for each child — is enough for its colour to be decided.
      </p>
      {some.length ? <Lines checks={some} /> : null}
      {none.length ? (
        <details data-unanswered className="group mt-2 border-t border-basalt/10 pt-2">
          <summary className="cursor-pointer text-[13.5px] text-basalt/75">
            {none.length} {none.length === 1 ? "skill" : "skills"} {unanswered}
          </summary>
          <Lines checks={none} />
        </details>
      ) : null}
    </Panel>
  );
}

function Lines({ checks }: { checks: Check[] }) {
  return (
    <ul className="grid">
      {checks.map((c) => (
        <li
          key={c.key}
          data-check={c.key}
          className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-basalt/10 py-2 text-[13.5px] first:border-t-0 sm:grid sm:grid-cols-[minmax(0,1fr)_minmax(0,200px)_auto_auto]"
        >
          <span className="min-w-0 basis-full font-medium text-basalt sm:basis-auto">{c.skill}</span>
          <span className="min-w-0 text-[13px]">{c.who}</span>
          <span className="fact whitespace-nowrap text-[12.5px] text-basalt/70">
            {c.n} questions · {c.level}
          </span>
          <Link href={c.href} className="whitespace-nowrap">
            Make this check →
          </Link>
        </li>
      ))}
    </ul>
  );
}
