import Link from "@/components/link";
import { Panel } from "@/components/shell";
import { engineGet } from "@/lib/engine";
import { decideProposal } from "./actions";

// What children's confirmed answers propose for the bank, still undecided (goals/s21-real-difficulty.yaml): a
// question far easier or harder than its level, with its evidence. A person removes it (its worksheets are rebuilt)
// or keeps it; the engine decides nothing on its own. If the engine cannot be reached, the bank page still opens.
type Mislevelled = {
  id: string;
  kind: "mislevelled";
  subject: string;
  direction: "easier" | "harder";
  evidence: { n: number; correct: number; difficulty: string; skill_set_code: string };
};
// A way of working children's unexplained wrong answers point to (goals/s22-learned-mistakes.yaml): code found the
// column rule that gives each of these answers; a person names it and adopts it, or rejects it.
type NewMistake = {
  id: string;
  kind: "new_mistake";
  subject: string;
  direction: string;
  evidence: { words: string; examples: { op: string; a: number; b: number; wrote: number }[] };
};
type Proposal = Mislevelled | NewMistake;

async function open(): Promise<Proposal[] | null> {
  try {
    const res = await engineGet("/bank/proposals");
    return res.ok ? ((await res.json()) as Proposal[]) : null;
  } catch {
    return null;
  }
}

export async function Proposals() {
  const all = await open();
  const rows = all?.filter((p): p is Mislevelled => p.kind === "mislevelled") ?? null;
  const mistakes = all?.filter((p): p is NewMistake => p.kind === "new_mistake") ?? [];
  if (rows === null)
    return (
      <Panel title="What children's answers propose">
        <p className="text-[14px]">The engine could not be reached, so the proposals cannot be shown just now.</p>
      </Panel>
    );
  return (
    <Panel title="What children's answers propose" aside={rows.length + mistakes.length ? `${rows.length + mistakes.length} to decide` : "nothing to decide"}>
      <NewMistakes rows={mistakes} />
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="grid" aria-label="Questions far off their level">
            <thead>
              <tr>
                <th>Question</th>
                <th className="num">Level</th>
                <th className="num">Right</th>
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
                  <td className="num">{p.evidence.difficulty}</td>
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

function NewMistakes({ rows }: { rows: NewMistake[] }) {
  if (!rows.length) return null;
  const sign = (op: string) => (op === "-" ? "−" : op);
  return (
    <div className="mb-4 grid gap-3">
      <p className="text-[14px]">
        Children wrote these wrong answers and no named mistake explains them. The same way of working gives every one
        of them, on different questions. Name it to have it recognised from now on, or reject it.
      </p>
      {rows.map((p) => (
        <form key={p.id} action={decideProposal} className="grid gap-2 border-b pb-3 text-[14px]">
          <input type="hidden" name="id" value={p.id} />
          <p>
            <strong>{p.evidence.words}</strong>
          </p>
          <p>
            Seen as:{" "}
            {p.evidence.examples.map((e) => `${e.a} ${sign(e.op)} ${e.b} → ${e.wrote}`).join(" · ")}
          </p>
          <label className="flex flex-wrap items-center gap-2">
            Its name
            <input name="name" className="input min-w-[260px]" placeholder="how a teacher would say it" />
          </label>
          <div className="flex gap-2">
            <button name="verdict" value="adopt" className="btn">
              Adopt it as a mistake
            </button>
            <button name="verdict" value="reject" className="btn">
              Reject
            </button>
          </div>
        </form>
      ))}
    </div>
  );
}
