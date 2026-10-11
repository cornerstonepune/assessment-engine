import Link from "@/components/link";
import { Panel } from "@/components/shell";
import type { TopicStanding } from "@/lib/profile";

// A child's profile by topic (goals/ui4b1-child-by-topic.yaml). Nimish, 2026-10-11: "It should be by topic or
// something … what the entire profile of the child will look like." One row per topic they are taught, each count the
// skills where the graph's states put them; a topic opens its skills further down the page.
const COLUMNS = [
  ["red", "Needs help"],
  ["amber", "Practising"],
  ["green", "Secure"],
  ["grey", "Too few answers"],
  ["notYet", "Not assessed yet"],
] as const;

export function TopicProfile({ topics }: { topics: TopicStanding[] }) {
  if (!topics.length) return null;
  return (
    <Panel id="by-topic" label="Their profile by topic" title="By topic" aside="each skill counted once, where their checked answers put it">
      <div className="overflow-x-auto">
        <table className="grid" aria-label="By topic">
          <thead>
            <tr>
              <th>Topic</th>
              {COLUMNS.map(([, words]) => (
                <th key={words} className="num">
                  {words}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {topics.map((t) => (
              <tr key={t.code}>
                <td>
                  <Link href={`#topic-${t.code}`}>{t.name}</Link>
                </td>
                {COLUMNS.map(([k, words]) => (
                  <td key={k} className={`num ${k === "red" && t.red ? "font-semibold text-terracotta" : ""}`} aria-label={`${t.name}, ${words}: ${t[k]}`}>
                    {t[k] ? t[k] : <span className="text-basalt/35">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
