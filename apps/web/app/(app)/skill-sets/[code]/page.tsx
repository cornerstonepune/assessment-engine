import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Answers, KIND, mistakeOf, Question } from "@/components/question";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import {
  DIFFICULTIES,
  gradeWords,
  levelsOf,
  skillSets,
  type Difficulty,
} from "@/lib/queries";
import { mistakeBook } from "@/lib/queries-bank";
import { levelExamples, skillKinds, skillMistakes } from "@/lib/queries-skills";
import { worksheets } from "@/lib/queries-worksheets";
import { kindsInWords } from "../../worksheets/library";
import { approveSkills } from "./actions";

type Props = {
  params: Promise<{ code: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};

const fmtDate = (d: string) =>
  new Date(d)
    .toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    })
    .replace(/ /g, "-");

// One skill as a teacher reads it: what the child can do, what that looks like at each level with a
// real question from the bank, the kinds of question that test it, the mistakes it watches for, and
// its worksheets. Codes are provenance at the foot of the page, never the lead.
export default async function SkillPage({ params, searchParams }: Props) {
  const [{ code }, q] = await Promise.all([params, searchParams]);
  const level = DIFFICULTIES.find((d) => d === q.level);
  const [sets, examples, kinds, caught, book, sheets] = await deadline(
    Promise.all([
      skillSets(),
      levelExamples(code),
      skillKinds(code),
      skillMistakes(code),
      mistakeBook(),
      worksheets({ set: code, level }, 200, 0),
    ]),
  );
  const s = sets.find((x) => x.code === code);
  if (!s) notFound();
  const example = (d: Difficulty) => examples.find((e) => e.difficulty === d);
  const ops = new Set(
    DIFFICULTIES.map((d) => s.difficulty[d]?.check?.op).filter(Boolean),
  );
  const op = ops.size === 1 ? String([...ops][0]) : undefined;
  const mistakes = caught
    .map((m) => ({ ...m, said: mistakeOf(book, m.code, op) }))
    .filter((m) => m.said);

  return (
    <>
      <PageHeader
        stage={`${gradeWords(s.band)} · Skill ${sets.indexOf(s) + 1} of ${sets.length} · ${s.name}`}
        title={s.learning_objective}
        sub="What this skill looks like at each level, each with a real question from the bank, the mistakes its questions are built to catch, and its worksheets."
      />
      <Body>
        {q.saved ? (
          <Notice tone="neem">
            Saved. The new words wait for approval before they are the
            skill&rsquo;s words.
          </Notice>
        ) : null}
        {q.approved ? (
          <Notice tone="neem">Approved as written, in your name.</Notice>
        ) : null}

        <div className="mb-[18px] flex flex-wrap items-center gap-3">
          <Link href="/" className="chip">
            ← Curriculum
          </Link>
          {s.status === "ratified" ? (
            <Pill tone="neem">Approved · {s.ratified_by?.split(" (")[0]}</Pill>
          ) : (
            <form
              action={approveSkills}
              className="flex flex-wrap items-center gap-3"
            >
              <Pill tone="bamboo">Waiting for approval</Pill>
              <input type="hidden" name="code" value={s.code} />
              <input type="hidden" name="version" value={s.version} />
              <input
                type="hidden"
                name="back"
                value={`/skill-sets/${s.code}`}
              />
              <button className="btn" type="submit">
                Approve as written
              </button>
            </form>
          )}
          <Link href={`/skill-sets/${s.code}/edit`} className="chip">
            Change the words
          </Link>
        </div>

        <div className="grid gap-[18px]">
          <Panel
            title="At each level"
            aside="the level in words, and a real question from the bank"
          >
            <div className="grid gap-[14px] md:grid-cols-2 xl:grid-cols-4">
              {levelsOf(s).map((d) => {
                const it = example(d);
                return (
                  <section
                    key={d}
                    aria-label={d}
                    className="grid content-start gap-2 border border-basalt/12 p-3"
                  >
                    <h3 className="text-[15px]">{d}</h3>
                    <p className="text-[13.5px] leading-snug">
                      {s.difficulty[d]?.words}
                    </p>
                    {it ? (
                      <div className="grid gap-1 bg-chalk p-2 text-[13.5px]">
                        <span className="label">For example</span>
                        <Link
                          href={`/library/${it.item_key}`}
                          className="text-basalt no-underline"
                        >
                          <Question it={it} />
                        </Link>
                        <span className="text-[12.5px] text-basalt/62">
                          Answer: <Answers it={it} />
                        </span>
                      </div>
                    ) : (
                      <p className="note">
                        No question in the bank at this level yet.
                      </p>
                    )}
                    <p className="note">
                      <Link
                        href={`/library?set=${s.code}&difficulty=${d}#questions`}
                      >
                        {s.counts[d] ?? 0} questions
                      </Link>
                      {" · "}
                      {s.worksheets[d] ? (
                        <Link
                          href={`/skill-sets/${s.code}?level=${d}#worksheets`}
                        >
                          {s.worksheets[d]} worksheets
                        </Link>
                      ) : (
                        "no worksheets yet"
                      )}
                    </p>
                  </section>
                );
              })}
            </div>
          </Panel>

          <Panel
            title="Kinds of question"
            aside={`${kinds.length} ${kinds.length === 1 ? "kind" : "kinds"}`}
          >
            <div className="overflow-x-auto">
              <table className="grid" aria-label="Kinds of question">
                <thead>
                  <tr>
                    <th>Kind</th>
                    <th>For example</th>
                    <th className="text-right">Questions</th>
                  </tr>
                </thead>
                <tbody>
                  {kinds.map((k) => (
                    <tr key={k.fmt}>
                      <td className="whitespace-nowrap">
                        {KIND[k.fmt] ?? k.fmt}
                      </td>
                      <td>
                        <Link
                          href={`/library/${k.item_key}`}
                          className="text-basalt no-underline"
                        >
                          <Question it={k} />
                        </Link>
                      </td>
                      <td className="num">{k.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel
            title="Mistakes it watches for"
            aside="the wrong answers its questions are built to recognise"
          >
            {mistakes.length ? (
              <>
                <ul className="grid gap-3">
                  {mistakes.slice(0, 6).map((m) => (
                    <Mistake
                      key={m.code}
                      name={m.said!.name}
                      example={m.said!.description}
                      n={m.n}
                      code={m.code}
                    />
                  ))}
                </ul>
                {mistakes.length > 6 ? (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-[13.5px]">
                      {mistakes.length - 6} more mistakes
                    </summary>
                    <ul className="mt-3 grid gap-3">
                      {mistakes.slice(6).map((m) => (
                        <Mistake
                          key={m.code}
                          name={m.said!.name}
                          example={m.said!.description}
                          n={m.n}
                          code={m.code}
                        />
                      ))}
                    </ul>
                  </details>
                ) : null}
              </>
            ) : (
              <p className="note">
                This skill is marked by a person reading the child&rsquo;s
                words, so no wrong answer names a mistake on its own.
              </p>
            )}
          </Panel>

          <section id="worksheets" className="scroll-mt-6">
            <Panel
              title="Worksheets"
              aside={`${sheets.length} ${level ? `at ${level}` : "at every level"}`}
            >
              <div
                className="mb-3 flex flex-wrap items-center gap-2"
                aria-label="Show worksheets for"
              >
                <Link
                  href={`/skill-sets/${s.code}#worksheets`}
                  className={`chip ${level ? "" : "on"}`}
                >
                  Every level
                </Link>
                {levelsOf(s).map((d) => (
                  <Link
                    key={d}
                    href={`/skill-sets/${s.code}?level=${d}#worksheets`}
                    className={`chip ${level === d ? "on" : ""}`}
                  >
                    {d} · {s.worksheets[d] ?? 0}
                  </Link>
                ))}
              </div>
              {sheets.length ? (
                <div className="overflow-x-auto">
                  <table
                    className="grid"
                    aria-label="Worksheets for this skill"
                  >
                    <thead>
                      <tr>
                        <th>Worksheet</th>
                        <th>Level</th>
                        <th>Its twelve questions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sheets.map((w) => (
                        <tr key={w.code}>
                          <td className="fact whitespace-nowrap">
                            <Link href={`/worksheets/${w.code}`}>{w.code}</Link>
                          </td>
                          <td>{w.difficulty}</td>
                          <td className="text-[12.5px] text-basalt/70">
                            {kindsInWords(w.kinds)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="note">
                  No worksheets at this level: it holds too few questions to
                  fill one.
                </p>
              )}
            </Panel>
          </section>
        </div>

        <p className="fact mt-[18px] text-[11px] text-basalt/50">
          {s.code} · {s.rung_code} · version {s.version} · last changed{" "}
          {fmtDate(s.updated_at)}
        </p>
      </Body>
    </>
  );
}

function Mistake({
  name,
  example,
  n,
  code,
}: {
  name: string;
  example: string | null;
  n: number;
  code: string;
}) {
  return (
    <li className="grid gap-[2px] text-[13.5px]">
      <span>{name}</span>
      {example ? <span className="text-basalt/70">{example}</span> : null}
      <span className="note">
        caught by {n} {n === 1 ? "question" : "questions"}{" "}
        <span className="fact ml-1 text-[10.5px] text-basalt/45">{code}</span>
      </span>
    </li>
  );
}
