import { notFound } from "next/navigation";
import Link from "@/components/link";
import { Answers, KIND, mistakeOf, Question } from "@/components/question";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { levels } from "@/lib/levels";
import {
  gradeOf,
  grades,
  levelsOf,
  skillSets,
  type Difficulty,
} from "@/lib/queries";
import { mistakeBook } from "@/lib/queries-bank";
import { levelExamples, skillKinds, skillMistakes } from "@/lib/queries-skills";
import { worksheets } from "@/lib/queries-worksheets";
import { kindsInWords } from "../../worksheets/library";
import { approveSkills, saveGrades } from "./actions";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { mayDecide } from "@/lib/decides";
import { LevelApproval } from "./level-approval";

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
  const me = await requireStaff();
  const mayApprove = await deadline(mayDecide(me, "skills"));
  const [{ code }, q] = await Promise.all([params, searchParams]);
  const level = (await levels()).order.find((d) => d === q.level);
  const everyLevel = q.level === "all";
  const [all, examples, kinds, caught, book, sheets, g] = await deadline(
    Promise.all([
      skillSets({ untaught: true, scope: scopeOf(me) }),
      levelExamples(code),
      skillKinds(code),
      skillMistakes(code),
      mistakeBook(),
      worksheets({ set: code, level }, 200, 0),
      grades(),
    ]),
  );
  // a skill whose topic is not taught yet opens too, to be read and approved before it is switched on (goals/ny1-needs-you.yaml)
  const s = all.find((x) => x.code === code);
  if (!s) notFound();
  const sets = all.filter((x) => x.taught);
  const example = (d: Difficulty) => examples.find((e) => e.difficulty === d);
  const ops = new Set(levelsOf(s).map((d) => s.difficulty[d]?.check?.op).filter(Boolean));
  const op = ops.size === 1 ? String([...ops][0]) : undefined;
  // the worksheets of one level at a time (goals/ui3-curriculum.yaml): the one asked for, every one when asked, else the
  // first that has any — a skill's 73 worksheets listed at once were a page of codes
  const shownLevel = level ?? (everyLevel ? undefined : levelsOf(s).find((d) => sheets.some((w) => w.difficulty === d)));
  const shown = shownLevel ? sheets.filter((w) => w.difficulty === shownLevel) : sheets;
  const mistakes = caught
    .map((m) => ({ ...m, said: mistakeOf(book, m.code, op) }))
    .filter((m) => m.said);

  return (
    <>
      <PageHeader
        stage={`Curriculum · ${g.name(s.band)} · ${s.taught ? `Skill ${sets.indexOf(s) + 1} of ${sets.length}` : "Not taught yet"} · ${s.name}`}
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
        {q.approved === "0" ? (
          <Notice tone="terracotta">Nothing was approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.approved ? (
          <Notice tone="neem">Approved as written, in your name.</Notice>
        ) : null}
        {s.taught ? null : (
          <Notice tone="terracotta">
            Not taught yet: no class you see has been taught {s.topic_name ?? "its topic"}, so this skill is on none of
            their pages or papers. Read and approve it now; <Link href="/#not-taught">say a class has been taught it</Link>{" "}
            when one has.
          </Notice>
        )}

        <div id="means" className="mb-[18px] flex scroll-mt-6 flex-wrap items-center gap-3">
          <Link href="/" className="chip">
            ← Curriculum
          </Link>
          {s.status === "ratified" ? (
            <Pill tone="neem">Approved · {s.ratified_by?.split(" (")[0]}</Pill>
          ) : !mayApprove ? (
            // approving a skill is the coordinator's (people.decides); an educator is not offered it (goals/ux1-who-sees-what.yaml)
            <Pill tone="bamboo">Waiting for the coordinator&rsquo;s approval</Pill>
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

        {/* the skill in five parts, each one click from here (goals/ui3-curriculum.yaml) */}
        <nav aria-label="Parts of this skill" className="mb-[18px] flex flex-wrap gap-2">
          {[["What it means", "#means"], ["Levels", "#levels"], ["Mistakes", "#mistakes"], ["Questions", `/library?set=${s.code}#questions`], ["Worksheets", "#worksheets"]].map(([words, href]) => (
            <Link key={words} href={href} className="chip">{words}</Link>
          ))}
        </nav>

        <div className="grid gap-[18px]">
          <Panel
            title="Which grade each level belongs to"
            label="Which grade each level belongs to"
            aside="each level to one grade; a child is given a level of their grade or below"
          >
            {q.grades ? <Notice tone="neem">Saved: each level is now taught in the grade shown.</Notice> : null}
            <form action={saveGrades} className="flex flex-wrap items-end gap-4">
              <input type="hidden" name="code" value={s.code} />
              {levelsOf(s).map((d) => (
                <label key={d} className="grid gap-1 text-[13px]">
                  <span className="label">{d}</span>
                  <select name={`grade:${d}`} defaultValue={gradeOf(s, d)} className="border border-basalt/20 bg-white px-2 py-1">
                    {g.list.map((x) => (
                      <option key={x.code} value={x.code}>
                        {x.name}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <button className="btn secondary" type="submit">
                Save the grades
              </button>
            </form>
            <p className="note mt-2">
              A level in another grade shows under that grade on the Curriculum too. Moving a level does not change its
              words, so the skill keeps its approval.
              {s.moved_by && s.moved_at
                ? ` Last moved by ${s.moved_by}, ${new Date(s.moved_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}.`
                : null}
            </p>
          </Panel>
          <Panel
            id="levels"
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
                    <LevelApproval s={s} d={d} mayApprove={mayApprove} />
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
                    <th className="num">Questions</th>
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
            id="mistakes"
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
              aside={`${shown.length} ${shownLevel ? `at ${shownLevel}` : "at every level"}`}
            >
              <div
                className="mb-3 flex flex-wrap items-center gap-2"
                aria-label="Show worksheets for"
              >
                <Link
                  href={`/skill-sets/${s.code}?level=all#worksheets`}
                  className={`chip ${shownLevel ? "" : "on"}`}
                >
                  Every level
                </Link>
                {levelsOf(s).map((d) => (
                  <Link
                    key={d}
                    href={`/skill-sets/${s.code}?level=${d}#worksheets`}
                    className={`chip ${shownLevel === d ? "on" : ""}`}
                  >
                    {d} · {s.worksheets[d] ?? 0}
                  </Link>
                ))}
              </div>
              {shown.length ? (
                <div className="overflow-x-auto">
                  <table
                    className="grid"
                    aria-label="Worksheets for this skill"
                  >
                    <thead>
                      <tr>
                        <th>Worksheet</th>
                        <th className="num">Level</th>
                        <th>Its twelve questions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {shown.map((w) => (
                        <tr key={w.code}>
                          <td className="whitespace-nowrap">
                            {/* named by its level and number; the code printed on the sheet beside it */}
                            <Link href={`/worksheets/${w.code}`}>
                              {w.difficulty} · sheet {Number(w.code.split("-").pop()!.slice(1))}
                            </Link>{" "}
                            <span className="fact text-[11px] text-basalt/45">{w.code}</span>
                          </td>
                          <td className="num">{w.difficulty}</td>
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

function Mistake({ name, example, n }: { name: string; example: string | null; n: number }) {
  return (
    <li className="grid gap-[2px] text-[13.5px]">
      <span>{name}</span>
      {example ? <span className="text-basalt/70">{example}</span> : null}
      <span className="note">
        caught by {n} {n === 1 ? "question" : "questions"}
      </span>
    </li>
  );
}
