import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { kindWords } from "@/components/question";
import type { Trust, Week } from "@/lib/queries-today";
import { weekWords } from "@/lib/week";
import type { Column } from "@/lib/ux-rules";

// Whether checking pays (goals/ny2-the-queue-shrinks.yaml): each week's answers, how many a person had to check, and how
// near the reader is to settling a kind of question alone. Every wrong and blank still waits for a person (ADR 0029).
const WEEK_COLUMNS: Column<Week>[] = [
  { key: "week", label: "Week", value: (k) => weekWords(k.week), cell: (k) => <Link href={`/papers?week=${k.week}`}>{weekWords(k.week)}</Link> },
  { key: "read", label: "Answers read", num: true, value: (k) => k.read },
  { key: "alone", label: "Settled by the engine alone", num: true, value: (k) => k.alone },
  { key: "person", label: "Checked by a person", num: true, value: (k) => k.person },
  { key: "waiting", label: "Still waiting", num: true, value: (k) => k.waiting },
  { key: "needed", label: "Needed a person", num: true, value: (k) => `${Math.round((100 * (k.person + k.waiting)) / k.read)}%` },
];

export function Shrinking({ weeks, trust, words, page }: { weeks: Week[]; trust: Trust; words: Record<string, string>; page: number }) {
  const title = "Is the queue shrinking?";
  return (
    <section aria-label={title} className="panel mb-6 p-4">
      <h2 className="font-heading text-[17px]">{title}</h2>
      {/* in an educator's words, not the reader's (goals/ux8c-one-word.yaml) */}
      <p className="mt-1 text-[13.5px] leading-snug">
        The reader settles a right answer by itself only on a kind of question it has earned trust on. It is trusted on{" "}
        {trust.kinds ? `${trust.trusted} of ${trust.kinds}` : "none of the"} kinds of question it has read so far
        {trust.nearest
          ? `; the closest, ${kindWords(words, trust.nearest.fmt)}, needs ${trust.nearest.to_trust} more ${trust.nearest.to_trust === 1 ? "answer" : "answers"} where a person agrees with what it read`
          : ""}
        . Every wrong answer and every blank still waits for a person.
      </p>
      {weeks.length ? (
        <div className="mt-3 min-w-0">
          <DataTable label="Answers read, week by week" columns={WEEK_COLUMNS} rows={weeks} rowKey={(k) => k.week} more={{ page, href: (p: number) => `/today?weeks=${p}` }} />
        </div>
      ) : (
        <p className="note mt-2">No papers read yet.</p>
      )}
    </section>
  );
}
