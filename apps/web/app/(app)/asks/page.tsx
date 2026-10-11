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
        stage="Curriculum"
        title="Questions to answer"
        sub="What the engine drafted about the curriculum and wants a person to agree with or correct. Open one to read it; agree as drafted, or write what it should say. Your name goes on it, and the next change is built from what you said."
      />
      <Body>
        <Link href="/" className="chip mb-[18px] inline-block">
          ← Curriculum
        </Link>
        {q.empty ? <Notice tone="terracotta">A correction needs its words: write what it should say.</Notice> : null}
        {mineFirst.length === 0 ? <Notice tone="neem">Every question is answered.</Notice> : null}
        <div className="grid gap-[10px]">
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

// One question, one line until it is opened (goals/ui3-curriculum.yaml): thirty of them in full were 10,700 pixels.
function Question({ a, me }: { a: Ask; me: string }) {
  return (
    <section aria-label={a.question} className="panel">
      <details>
        <summary className="panel-head cursor-pointer">
          <h2 className="text-[15.5px]">{a.question}</h2>
          <span className="fact text-[11px] text-basalt/55">for {ROLE_WORDS[a.for_role] ?? a.for_role}</span>
        </summary>
        <div className="panel-body">
          <p className="text-[15px] leading-snug">{a.drafted}</p>
          {a.why ? <p className="mt-2 text-[13px] text-basalt/70">Why: {a.why}</p> : null}
          {a.link ? (
            <p className="mt-2 text-[12px] text-basalt/55">
              <a href={a.link}>Read it in full</a>
            </p>
          ) : null}
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
        </div>
      </details>
    </section>
  );
}
