import Link from "@/components/link";
import { Pill } from "@/components/shell";
import { STAGE_WORDS, type PaperListRow, type Stage } from "@/lib/queries-papers";

// A stage's material: what waits on a person reads warm, what is done reads settled (pills never red or green).
export const STAGE_TONE: Record<Stage, "neem" | "bamboo" | "terracotta" | "monsoon"> = {
  made: "monsoon",
  printed: "monsoon",
  scanned: "terracotta",
  checked: "bamboo",
  "signed off": "neem",
  replaced: "monsoon",
};

// Where a paper's work is: its answers once it is read, the page itself before.
export const opens = (p: PaperListRow) =>
  p.stage === "made" || p.stage === "printed" || p.stage === "replaced" ? `/worksheets/${encodeURIComponent(p.qr)}` : `/capture/${p.id}`;

// An assessment's copies (goals/ux5-papers-grouped.yaml): one row each in roll order, its child opening the paper where
// its work is; the spares, not yet written on, one line under them — they go with the pack and wait for no one.
export function CopiesTable({ title, rows }: { title: string; rows: PaperListRow[] }) {
  const copies = rows.filter((p) => !p.spare);
  const spares = rows.filter((p) => p.spare);
  return (
    <div className="pb-2">
      {copies.length ? (
        <table className="grid" aria-label={`${title}: each copy`}>
          <thead>
            <tr>
              <th>Roll</th>
              <th>Child</th>
              <th>Level</th>
              <th>Stage</th>
              <th className="num">Waiting</th>
              <th className="num">Score</th>
            </tr>
          </thead>
          <tbody>
            {copies.map((p) => (
              <tr key={p.id} data-paper={p.id}>
                <td className="fact">{p.roll_no ?? <span className="text-basalt/45">—</span>}</td>
                <td>
                  <Link href={opens(p)} className="font-medium">
                    {p.child ?? "spare copy"}
                  </Link>
                </td>
                <td>{p.level ?? <span className="text-basalt/45">—</span>}</td>
                <td>
                  <Pill tone={STAGE_TONE[p.stage]}>{STAGE_WORDS[p.stage]}</Pill>
                </td>
                <td className="num">{p.waiting ? p.waiting : <span className="text-basalt/45">—</span>}</td>
                <td className="num whitespace-nowrap">
                  {(p.stage === "checked" || p.stage === "signed off") && p.scored ? `${p.right} of ${p.scored}` : <span className="text-basalt/45">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {spares.length ? (
        <p data-spares className="mt-2 text-[12.5px] text-basalt/70">
          {spares.length} spare {spares.length === 1 ? "copy" : "copies"}, with the pack:{" "}
          {spares.map((p, i) => (
            <span key={p.id}>
              <Link href={opens(p)} className="fact">
                {p.qr}
              </Link>
              {i < spares.length - 1 ? ", " : ""}
            </span>
          ))}
        </p>
      ) : null}
    </div>
  );
}
