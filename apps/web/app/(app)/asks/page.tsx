import Link from "@/components/link";
import { Body, Notice, PageHeader, Panel } from "@/components/shell";
import { requireStaff } from "@/lib/auth";
import { deadline } from "@/lib/deadline";
import { type Ask, asks, ROLE_WORDS } from "@/lib/queries-people";
import { answerAsk } from "./actions";

type Props = { searchParams: Promise<Record<string, string | undefined>> };

// Questions to answer (goals/ny1-needs-you.yaml): everything the engine drafted for a person — the taxonomy, its
// assumptions, each slice's decisions — each with what it drafted and why, agreed as drafted or corrected in the
// person's own words, in their name. Yours first; the answered ones below, with who answered and what they said.
export default async function Asks({ searchParams }: Props) {
  const me = await requireStaff();
  const [all, q] = await Promise.all([deadline(asks()), searchParams]);
  const open = all.filter((a) => !a.answer);
  const mineFirst = [...open.filter((a) => a.for_role === me.role), ...open.filter((a) => a.for_role !== me.role)];
  const answered = all.filter((a) => a.answer);

  return (
    <>
      <PageHeader
        stage="Today"
        title="Questions to answer"
        sub="What the engine drafted and wants a person to agree with or correct. Agree as drafted, or write what it should say; your name goes on it, and the next change is built from what you said."
      />
      <Body>
        <Link href="/today" className="chip mb-[18px] inline-block">
          ← Today
        </Link>
        {q.empty ? <Notice tone="terracotta">A correction needs its words: write what it should say.</Notice> : null}
        {mineFirst.length === 0 ? <Notice tone="neem">Every question is answered.</Notice> : null}
        <div className="grid gap-[18px]">
          {mineFirst.map((a) => (
            <Question key={a.code} a={a} me={me.name} />
          ))}
          {answered.length ? (
            <Panel title="Answered" label="Answered" aside={`${answered.length}`}>
              <ul className="grid gap-3 text-[13.5px]">
                {answered.map((a) => (
                  <li key={a.code}>
                    <b>{a.question}</b>
                    <span className="block text-basalt/70">
                      {a.answer === "agreed" ? "Agreed as drafted" : "Corrected"} by {a.answered_by}, {a.answered_at?.slice(0, 10)}
                    </span>
                    {a.correction ? <span className="block">It should say: {a.correction}</span> : null}
                  </li>
                ))}
              </ul>
            </Panel>
          ) : null}
        </div>
      </Body>
    </>
  );
}

function Question({ a, me }: { a: Ask; me: string }) {
  return (
    <Panel title={a.question} label={a.question} aside={`for ${ROLE_WORDS[a.for_role] ?? a.for_role}`}>
      <p className="text-[15px] leading-snug">{a.drafted}</p>
      {a.why ? <p className="mt-2 text-[13px] text-basalt/70">Why: {a.why}</p> : null}
      <p className="mt-2 text-[12px] text-basalt/55">
        Drafted in {a.source}
        {a.link ? (
          <>
            {" "}
            · <a href={a.link}>read it in full</a>
          </>
        ) : null}
      </p>
      <div className="mt-3 flex flex-wrap items-start gap-3">
        <form action={answerAsk}>
          <input type="hidden" name="code" value={a.code} />
          <input type="hidden" name="answer" value="agreed" />
          <button className="btn" type="submit">
            Agree as drafted, as {me}
          </button>
        </form>
        <form action={answerAsk} className="grid flex-1 gap-2">
          <input type="hidden" name="code" value={a.code} />
          <input type="hidden" name="answer" value="corrected" />
          <label className="grid gap-1 text-[13px]">
            What it should say
            <textarea name="correction" rows={2} className="border border-basalt/35 p-2" />
          </label>
          <button className="chip self-start" type="submit">
            Correct it, as {me}
          </button>
        </form>
      </div>
    </Panel>
  );
}
