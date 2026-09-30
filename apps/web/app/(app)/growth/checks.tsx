import type { ReactNode } from "react";
import Link from "@/components/link";
import { Panel } from "@/components/shell";

export type Check = { key: string; skill: string; who: ReactNode; level: string; n: number; href: string };

// Where the colours cannot say yet — grey, or no answer at all — the check that would place the child
// (goals/u11-colours-said.yaml). Nimish, 2026-09-30: "for areas where we don't have sufficient data points … we should
// have a clear recommendation around the next set of assessments … so that we know where the child is". Each check
// opens in the maker, its children, skill, level and size already chosen; nothing prints until an educator makes it.
export function ChecksPanel({ title, whoHeading, checks }: { title: string; whoHeading: string; checks: Check[] }) {
  if (!checks.length) return null;
  return (
    <Panel title={title} label={title} aside={`${checks.length} ${checks.length === 1 ? "skill" : "skills"}`}>
      <p className="note mb-3">
        A skill is grey until it has enough checked answers to say. One short class assessment on it — at the grade&rsquo;s starting
        level, different questions for each child — is enough for its colour to be decided.
      </p>
      <div className="overflow-x-auto">
        <table className="grid" aria-label={title}>
          <thead>
            <tr>
              <th>Skill</th>
              <th>{whoHeading}</th>
              <th className="num">The check</th>
              <th className="num"></th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={c.key} data-check={c.key}>
                <td className="min-w-[180px]">{c.skill}</td>
                <td className="text-[13px]">{c.who}</td>
                <td className="num whitespace-nowrap">
                  {c.n} questions · {c.level}
                </td>
                <td className="num whitespace-nowrap">
                  <Link href={c.href}>Make this check →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
