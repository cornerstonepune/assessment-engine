import Link from "@/components/link";
import { Panel } from "@/components/shell";
import { engineGet } from "@/lib/engine";
import { decideProposal } from "./actions";

// What children's confirmed answers propose for the bank, still undecided (goals/s21-real-difficulty.yaml): a
// question far easier or harder than its level, with its evidence. A person removes it (its worksheets are rebuilt)
// or keeps it; the engine decides nothing on its own. If the engine cannot be reached, the bank page still opens.
type Proposal = {
  id: string;
  subject: string;
  direction: "easier" | "harder";
  evidence: { n: number; correct: number; difficulty: string; skill_set_code: string };
};

async function open(): Promise<Proposal[] | null> {
  try {
    const res = await engineGet("/bank/proposals");
    return res.ok ? ((await res.json()) as Proposal[]) : null;
  } catch {
    return null;
  }
}

export async function Proposals() {
  const rows = await open();
  if (rows === null)
    return (
      <Panel title="What children's answers propose">
        <p className="text-[14px]">The engine could not be reached, so the proposals cannot be shown just now.</p>
      </Panel>
    );
  return (
    <Panel title="What children's answers propose" aside={rows.length ? `${rows.length} to decide` : "nothing to decide"}>
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="grid" aria-label="Questions far off their level">
            <thead>
              <tr>
                <th>Question</th>
                <th>Level</th>
                <th className="text-right">Right</th>
                <th>Children found it</th>
                <th>Decide</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link href={`/library/${p.subject}`}>{p.subject}</Link>
                  </td>
                  <td>{p.evidence.difficulty}</td>
                  <td className="num">
                    {p.evidence.correct} of {p.evidence.n}
                  </td>
                  <td>far {p.direction} than {p.evidence.difficulty}</td>
                  <td>
                    <form action={decideProposal} className="flex gap-2">
                      <input type="hidden" name="id" value={p.id} />
                      <button name="verdict" value="remove" className="btn">
                        Remove from the bank
                      </button>
                      <button name="verdict" value="keep" className="btn">
                        Keep it
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-[14px]">No question is far off its level in the answers people have confirmed.</p>
      )}
    </Panel>
  );
}
