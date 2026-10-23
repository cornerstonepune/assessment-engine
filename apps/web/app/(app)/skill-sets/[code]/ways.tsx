import { Panel, Pill } from "@/components/shell";
import type { WaysRow } from "@/lib/queries-skills";
import { dateWords } from "@/lib/week";
import { approveWay } from "./actions";

// A skill whose questions are not drawn from a bank (English, goals/e0-english-in-the-system.yaml) is read from the rows
// that say how it is asked and which mistakes it watches for. A way of asking that a person reads every answer of says so.

/** How one level is asked, on its card. */
export function LevelWays({ ways, level }: { ways: WaysRow[]; level: string }) {
  return (
    <ul className="grid gap-[3px] text-[12.5px] text-basalt/70" aria-label={`How ${level} is asked`}>
      {ways
        .filter((w) => w.levels.includes(level))
        .map((w) => (
          <li key={w.code}>
            {w.words}
            {w.open ? " · a person checks every answer" : ""}
          </li>
        ))}
    </ul>
  );
}

/** Every way the skill is asked, who checks it, and its approval: one approval covers every skill that asks it that way. */
export function WaysPanel({ ways, code, mayApprove }: { ways: WaysRow[]; code: string; mayApprove: boolean }) {
  return (
    <Panel id="ways" title="How it is asked" aside="approving one covers every skill that asks it that way">
      <div className="overflow-x-auto">
        <table className="grid" aria-label="How it is asked">
          <thead>
            <tr>
              <th>Way of asking</th>
              <th>Levels</th>
              <th>Checked by</th>
              <th>Approval</th>
            </tr>
          </thead>
          <tbody>
            {ways.map((w) => (
              <tr key={w.code} data-way={w.code}>
                <td>{w.words}</td>
                <td>{w.levels.join(", ")}</td>
                <td>{w.open ? "a person checks every answer" : "the system"}</td>
                <td>
                  {w.by && w.at ? (
                    <Pill tone="neem">
                      Approved · {w.by.split(" (")[0]} · {dateWords(w.at)}
                    </Pill>
                  ) : mayApprove ? (
                    <form action={approveWay}>
                      <input type="hidden" name="way" value={w.code} />
                      <input type="hidden" name="back" value={code} />
                      <button className="btn" type="submit">
                        Approve &ldquo;{w.words}&rdquo;
                      </button>
                    </form>
                  ) : (
                    <span className="note">Waiting for approval</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

/** The mistakes the skill watches for, in words. */
export function Watched({ watched }: { watched: { code: string; name: string; description: string }[] }) {
  if (!watched.length) return <p className="note">No mistake is named for this skill yet.</p>;
  return (
    <ul className="grid gap-3">
      {watched.map((m) => (
        <li key={m.code} className="grid gap-[2px] text-[13.5px]">
          <span>{m.name}</span>
          {m.description ? <span className="text-basalt/70">{m.description}</span> : null}
        </li>
      ))}
    </ul>
  );
}
