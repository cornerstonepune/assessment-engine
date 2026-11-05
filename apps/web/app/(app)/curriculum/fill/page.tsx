import Link from "@/components/link";
import { gap, gate, SLOT_WORDS, waiting } from "@/lib/curriculum-screens";
import { Icon } from "@/lib/icons";
import { Chrome, Empty } from "../chrome";

// Per part of the page: how many K2 activities hold the school's words, a draft waiting for a check, a person's
// words, or nothing. A person can walk the drafted ones one by one.
export default async function Fill() {
  await gate();
  const [rows, queue] = await Promise.all([gap(), waiting()]);
  const total = rows[0] ? rows[0].school + rows[0].drafted + rows[0].person + rows[0].empty : 0;
  return (
    <Chrome here="/curriculum/fill" title="What is filled, and by whom" lead={`For each part of the ${total} K2 activities: the school's own words, a draft waiting for a check, words a person kept, or still empty.`}>
      <div className="cs-actions" style={{ marginBottom: "var(--space-3)" }}>
        {queue.length ? (
          <Link href="/curriculum/fill/walk" className="cs-btn" data-main>
            <Icon name="checklist" size={16} /> Check the drafted parts ({queue.length})
          </Link>
        ) : (
          <Empty>Nothing is waiting for a check.</Empty>
        )}
      </div>
      <table className="cs-table">
        <thead>
          <tr><th>Part</th><th className="n">The school&apos;s</th><th className="n">Drafted, check me</th><th className="n">Kept by a person</th><th className="n">Empty</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.part} data-part={r.part}>
              <td>{SLOT_WORDS[r.part]}</td>
              <td className="n" data-count="school">{r.school}</td>
              <td className="n" data-count="drafted">{r.drafted > 0 ? <Link href={`/curriculum/fill/walk?part=${r.part}`}>{r.drafted}</Link> : r.drafted}</td>
              <td className="n" data-count="person">{r.person}</td>
              <td className="n" data-count="empty">{r.empty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Chrome>
  );
}
