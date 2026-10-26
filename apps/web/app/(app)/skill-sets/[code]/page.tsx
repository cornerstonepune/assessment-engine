import { notFound } from "next/navigation";
import Link from "@/components/link";
import { sheetWords } from "../../worksheets/[qr]/library-sheet";
import { Answers, kindWords, mistakeOf, Question } from "@/components/question";
import { questionKinds } from "@/lib/question-types";
import { Body, Notice, PageHeader, Panel, Pill } from "@/components/shell";
import { deadline } from "@/lib/deadline";
import { levels } from "@/lib/levels";
import {
  grades,
  levelsOf,
  skillSets,
  type Difficulty,
} from "@/lib/queries";
import { mistakeBook } from "@/lib/queries-bank";
import { levelExamples, openedAt, skillKinds, skillMistakes, skillSamples, skillWatches, skillWays } from "@/lib/queries-skills";
import { worksheets } from "@/lib/queries-worksheets";
import { kindsInWords } from "../../worksheets/library";
import { approveSkills } from "./actions";
import { requireStaff } from "@/lib/auth";
import { scopeOf } from "@/lib/scope";
import { mayDecide } from "@/lib/decides";
import { LevelApproval } from "./level-approval";
import { GradesPanel } from "./grades-panel";
import { Watched, WaysPanel } from "./ways";
import { KindStops } from "./kind-stops";
import { Changed, editingOf, EnglishLevel, MadeByCode, SentenceLink } from "./editing";
import { dateWords } from "@/lib/week";

type Props = {
  params: Promise<{ code: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};


// One skill as a teacher reads it: what the child can do, what that looks like at each level with a
// real question from the bank, the kinds of question that test it, the mistakes it watches for, and
// its worksheets. Codes are provenance at the foot of the page, never the lead. An English skill's samples and the kinds
// each level asks are changed here by whoever may change the skill (goals/edt_edit_samples_and_kinds.yaml).
export default async function SkillPage({ params, searchParams }: Props) {
  const me = await requireStaff();
  const [mayApprove, mayChange] = await deadline(Promise.all([mayDecide(me, "skills"), mayDecide(me, "skill_drafts")]));
  const [{ code }, q] = await Promise.all([params, searchParams]);
  const level = (await levels()).order.find((d) => d === q.level);
  const everyLevel = q.level === "all";
  const [all, examples, kinds, caught, book, sheets, g, { words }, ways, watched, samples, opened] = await deadline(
    Promise.all([
      skillSets({ untaught: true, scope: scopeOf(me) }),
      levelExamples(code),
      skillKinds(code),
      skillMistakes(code),
      mistakeBook(),
      worksheets({ set: code, level }, 200, 0),
      grades(),
      questionKinds(),
      skillWays(code),
      skillWatches(code),
      skillSamples(code), openedAt(),
    ]),
  );
  // a skill whose topic is not taught yet opens too, to be read and approved before it is switched on (goals/ny1-needs-you.yaml)
  const s = all.find((x) => x.code === code);
  if (!s) notFound();
  const sets = all.filter((x) => x.taught);
  // a skill whose questions are not drawn from the bank (English, E0) is read from the rows that say how it is asked
  const bankless = !Object.keys(s.counts).length && ways.length > 0;
  const example = (d: Difficulty) => examples.find((e) => e.difficulty === d);
  const ops = new Set(levelsOf(s).map((d) => s.difficulty[d]?.check?.op).filter(Boolean));
  const op = ops.size === 1 ? String([...ops][0]) : undefined;
  // the worksheets of one level at a time (goals/ui3-curriculum.yaml): the one asked for, every one when asked, else the
  // first that has any — a skill's 73 worksheets listed at once were a page of codes
  const shownLevel = level ?? (everyLevel ? undefined : levelsOf(s).find((d) => sheets.some((w) => w.difficulty === d)));
  const shown = shownLevel ? sheets.filter((w) => w.difficulty === shownLevel) : sheets;
  const editing = bankless && mayChange ? await deadline(editingOf(s.code, q)) : null;
  const mistakes = caught
    .map((m) => ({ ...m, said: mistakeOf(book, m.code, op) }))
    .filter((m) => m.said);

  // approve or change the words: at the top, or for a skill read from its samples (English), under them, so the
  // approver reads first (goals/smp_skill_shows_its_samples.yaml)
  const decide = (
    <>
      {s.status === "ratified" ? (
        <Pill tone="neem">Approved · {s.ratified_by?.split(" (")[0]}</Pill>
      ) : !mayApprove ? (
        // approving a skill is the coordinator's (people.decides); an educator is not offered it (goals/ux1-who-sees-what.yaml)
        <Pill tone="bamboo">Waiting for the coordinator&rsquo;s approval</Pill>
      ) : (
        <form action={approveSkills} className="flex flex-wrap items-center gap-3">
          <Pill tone="bamboo">Waiting for approval</Pill>
          <input type="hidden" name="code" value={s.code} />
          <input type="hidden" name="version" value={s.version} /><input type="hidden" name="opened" value={opened} />
          <input type="hidden" name="back" value={`/skill-sets/${s.code}`} />
          <button className="btn" type="submit">
            Approve, as {me.name}
          </button>
        </form>
      )}
      {/* what it changes, said (Nimish, 2026-10-24: "What does 'change the words first' do?") */}
      <Link href={`/skill-sets/${s.code}/edit`} className="chip">
        Change the description and each level&rsquo;s sentence
      </Link>
    </>
  );

  return (
    <>
      <PageHeader
        stage={`Curriculum · ${g.name(s.band)} · ${s.taught ? `Skill ${sets.indexOf(s) + 1} of ${sets.length}` : "Not taught yet"} · ${s.name}`}
        title={s.learning_objective}
        sub={bankless ? "What this skill looks like at each level, with sample questions, how it is asked, and the mistakes to watch for." : "What this skill looks like at each level, each with a real question from the bank, the mistakes its questions are built to catch, and its worksheets."}
      />
      <Body>
        <Changed q={q} />
        {q.saved ? (
          <Notice tone="neem">Saved. The new words wait for approval before they are the skill&rsquo;s words.</Notice>
        ) : null}
        {q.approved === "0" ? (
          <Notice tone="terracotta">Nothing was approved: it changed since this page was opened. Read it again, then approve.</Notice>
        ) : q.approved ? (
          <Notice tone="neem">Approved as written, in your name.</Notice>
        ) : null}
        {q.way_approved ? (
          <Notice tone="neem">
            Approved &ldquo;{ways.find((w) => w.code === q.way_approved)?.words ?? "this way of asking"}&rdquo;, in your name.
          </Notice>
        ) : null}
        {s.taught ? null : (
          <Notice tone="terracotta">
            Not taught yet: no class you see has been taught {s.topic_name ?? "its topic"}, so this skill is on none of
            their pages or papers. Read and approve it now; <Link href="/taught#not-taught">say a class has been taught it</Link>{" "}
            when one has.
          </Notice>
        )}

        <div id="means" className="mb-[18px] flex scroll-mt-6 flex-wrap items-center gap-3">
          <Link href="/" className="chip">
            ← Curriculum
          </Link>
          {bankless && s.status !== "ratified" ? (
            <Link href="#decide" className="chip">Read the sample questions, then approve ↓</Link>
          ) : (
            decide
          )}
        </div>

        {/* the skill in five parts, each one click from here (goals/ui3-curriculum.yaml) */}
        <nav aria-label="Parts of this skill" className="mb-[18px] flex flex-wrap gap-2">
          {(bankless
            ? [["What it means", "#means"], ["Levels", "#levels"], ["How it is asked", "#ways"], ["Mistakes", "#mistakes"]]
            : [["What it means", "#means"], ["Levels", "#levels"], ["Mistakes", "#mistakes"], ["Questions", `/library?set=${s.code}#questions`], ["Worksheets", "#worksheets"]]
          ).map(([words, href]) => (
            <Link key={words} href={href} className="chip">{words}</Link>
          ))}
        </nav>

        <div className="grid gap-[18px]">
          <GradesPanel s={s} grades={g} saved={Boolean(q.grades)} />
          <Panel
            id="levels"
            title="At each level"
            aside={bankless ? "what the child does at each level, its sample questions, and how it is asked" : "the level in words, and a real question from the bank"}
          >
            <div className={`grid gap-[14px] ${bankless ? "" : "md:grid-cols-2 xl:grid-cols-4"}`}>
              {levelsOf(s).map((d) => {
                const it = example(d);
                return (
                  <section
                    key={d} id={`level-${d}`}
                    aria-label={d}
                    className="grid scroll-mt-6 content-start gap-2 border border-basalt/12 p-3"
                  >
                    <h3 className="text-[15px]">{d}</h3>
                    {bankless ? null : <LevelApproval s={s} d={d} mayApprove={mayApprove} />}
                    <p className="text-[13.5px] leading-snug">
                      {s.difficulty[d]?.words}
                    </p>
                    {mayChange ? <SentenceLink code={s.code} level={d} /> : null}
                    {bankless ? (
                      <EnglishLevel s={s} level={d} ways={ways} samples={samples} editing={editing} mayApprove={mayApprove} opened={opened} />
                    ) : it ? (
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
                    {bankless ? null : <p className="note">
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
                    </p>}
                  </section>
                );
              })}
            </div>
            {!bankless && mayChange ? <MadeByCode /> : null}
            {bankless ? (
              <div id="decide" className="mt-[14px] flex scroll-mt-6 flex-wrap items-center gap-3">
                {decide}
              </div>
            ) : null}
          </Panel>

          {bankless ? (
            <WaysPanel ways={ways} code={s.code} mayApprove={mayApprove} />
          ) : (
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
                        {kindWords(words, k.fmt)}
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
          )}
          <KindStops code={s.code} ways={ways} levels={levelsOf(s)} q={q} mayChange={mayChange} />
          <Panel
            id="mistakes"
            title="Mistakes it watches for"
            aside="the wrong answers its questions are built to recognise"
          >
            {bankless ? (
              <Watched watched={watched} />
            ) : mistakes.length ? (
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

          {bankless ? null : <section id="worksheets" className="scroll-mt-6">
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
                              {w.difficulty} · {sheetWords(w.code)}
                            </Link>{" "}
                            <span className="fact text-[11px] text-basalt/45">{w.code}</span>
                          </td>
                          <td className="num">{w.difficulty}</td>
                          <td className="text-[12.5px] text-basalt/70">
                            {kindsInWords(w.kinds, words)}
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
          </section>}
        </div>

        <p className="fact mt-[18px] text-[11px] text-basalt/50">
          {s.code} · {s.rung_code} · version {s.version} · last changed{" "}
          {dateWords(s.updated_at)}
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
