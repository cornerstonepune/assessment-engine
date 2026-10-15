import Link from "@/components/link";
import { Swatch } from "@/components/colour-key";
import { NEED } from "@/lib/profile";
import { stepKey, type GridChild, type Step } from "@/lib/queries-children";
import { rag, type Rag } from "@/lib/rag";

// A class against its topics (goals/ui4b2-class-by-topic.yaml): its children down the side, across the top each topic
// someone in the class has answers in, each cell counting that child's skills in it by where the graph's states put
// them — every count in words beside its mark, the cell the colour of what needs help first. A topic's name opens the
// class against that topic's skills alone, in this table's place (goals/ux4-class-and-child.yaml). Counted here from the
// class's own grid, never decided here.
const WORDS: Record<Rag, string> = { red: "needs help", amber: "practising", green: "secure", grey: "too few answers" };
const ORDER: Rag[] = ["red", "amber", "green", "grey"];

export function TopicGrid({ section, steps, kids }: { section: string; steps: Step[]; kids: GridChild[] }) {
  const topics = [...new Map(steps.map((s) => [s.topic_code, s.topic_name])).entries()];
  if (!topics.length) return null;
  return (
    <div className="panel overflow-x-auto">
      <table className="grid" aria-label={`${section}: each child on each topic`}>
        <thead>
          <tr>
            <th className="pin">Child</th>
            {topics.map(([code, name]) => (
              <th key={code} data-topic={code} className="border-l border-basalt/12">
                <Link href={`/growth/class/${encodeURIComponent(section)}?topic=${code}`}>{name}</Link>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {kids.map((c) => (
            <tr key={c.id} data-child={c.id}>
              <td className="pin whitespace-nowrap">
                <span className="fact mr-2 text-basalt/55">{c.roll_no}</span>
                <Link href={`/growth/${c.id}`} className="underline decoration-basalt/30 underline-offset-4">
                  {c.first_name}
                </Link>
              </td>
              {topics.map(([code, name]) => {
                const n = count(c, steps.filter((s) => s.topic_code === code));
                const shown = ORDER.filter((r) => n[r]);
                return (
                  <td
                    key={code}
                    data-topic={code}
                    data-rag={shown.length ? [...shown].sort((a, b) => NEED[a] - NEED[b])[0] : undefined}
                    className="border-l border-basalt/12 text-[12.5px]"
                  >
                    {shown.length ? (
                      <span className="grid gap-1">
                        {shown.map((r) => (
                          <span key={r} className="inline-flex items-center gap-1.5 whitespace-nowrap">
                            <Swatch colour={r} label={`${c.first_name}, ${name}: ${n[r]} ${WORDS[r]}`} />
                            {n[r]} {WORDS[r]}
                          </span>
                        ))}
                      </span>
                    ) : (
                      <span className="text-basalt/30">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A child's skills in a topic counted by colour: those they have answered, each where its state puts it. */
function count(c: GridChild, steps: Step[]): Record<Rag, number> {
  const n: Record<Rag, number> = { red: 0, amber: 0, green: 0, grey: 0 };
  for (const s of steps) {
    const got = c.states[stepKey(s)];
    if (got?.n_events) n[rag(got.state)] += 1;
  }
  return n;
}
