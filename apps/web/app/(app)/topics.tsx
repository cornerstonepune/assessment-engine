import Link from "@/components/link";
import { Panel } from "@/components/shell";
import type { ClassTaught, Topic } from "@/lib/queries-people";
import { switchTopic } from "./topic-actions";
import { dateWords } from "@/lib/week";

// Which topics each class has been taught, and who said so (goals/f1f-taught-per-class.yaml): an educator says it of
// their own classes, the coordinator of any, in their own name; a class no one has spoken for follows the school's
// word. A topic not taught yet lists its skills, so a person knows what saying it brings; it is said from inside a
// fold, as one taught is unsaid, never by a stray click. Said of a topic, it is said of every skill in it. One class's
// skills of one topic open on their own (`?skills=TOPIC&in=CLASS`), each with its own switch, so a class can be taught
// Multiplication and not yet its columns (goals/t1-topics-are-operations.yaml) — never every class's every skill at
// once, a page of thousands of switches. A topic not taught yet is also a word on its row of the table; the two lists
// here are one fold, "Taught in each class", opened when asked for (goals/ux10-declutter.yaml).
export function Topics({ topics, me, open, fold = false }: { topics: Topic[]; me: string; open: { topic: string; section: string } | null; fold?: boolean }) {
  const off = topics.filter((t) => t.classes.some((c) => !c.taught));
  const on = topics.filter((t) => t.classes.some((c) => c.taught));
  const opened = open ? topics.find((t) => t.code === open.topic) : undefined;
  const skills = opened?.classes.find((c) => c.section === open?.section);
  return (
    <div className="mb-[18px] grid gap-[14px]">
      {opened && skills ? (
        <Panel title={`${opened.name} in ${skills.section}`} label="Skills of a topic in a class" id="skills" aside={`${skills.skills.filter((k) => k.taught).length} of ${skills.skills.length} skills taught`}>
          <ul className="grid gap-1 text-[13px]">
            {skills.skills.map((k) => (
              <li key={k.code} className="flex flex-wrap items-center justify-between gap-3" data-skill={k.code}>
                <span>
                  <Link href={`/skill-sets/${k.code}`}>{k.name}</Link> <span className="text-basalt/55">· {k.taught ? "taught" : "not taught yet"}</span>
                </span>
                <Switch
                  code={opened.code}
                  skill={k.code}
                  section={skills.section}
                  on={!k.taught}
                  label={k.taught ? `Not taught in ${skills.section} yet` : `Taught in ${skills.section}`}
                />
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
      <details className="grid gap-[14px]" open={fold || !!opened}>
      <summary className="cursor-pointer text-[12.5px] text-basalt/65 underline underline-offset-2">Taught in each class</summary>
        <Panel title="Not taught yet" label="Not taught yet" id="not-taught" aside={`${off.length} ${off.length === 1 ? "topic" : "topics"}`}>
          {off.length ? (
            <ul className="grid gap-3">
              {off.map((t) => {
                const waiting = t.classes.filter((c) => !c.taught);
                return (
                  <li key={t.code} className="flex flex-wrap items-center justify-between gap-3">
                    <span>
                      <b>{t.name}</b>
                      <span className="block text-[13px] text-basalt/70">
                        {t.skills.map((k, i) => (
                          <span key={k.code}>
                            {i ? " · " : ""}
                            <Link href={`/skill-sets/${k.code}`}>{k.name}</Link>
                          </span>
                        ))}
                      </span>
                      {waiting.length > 8 ? (
                        <details className="text-[12px] text-basalt/55">
                          <summary className="cursor-pointer">Not taught yet in {waiting.length} classes</summary>
                          <p>{waiting.map((c) => c.section).join(", ")}</p>
                        </details>
                      ) : (
                        <span className="block text-[12px] text-basalt/55">Not taught yet in {waiting.map((c) => c.section).join(", ")}</span>
                      )}
                    </span>
                    <details className="text-right">
                      <summary className="btn secondary cursor-pointer list-none">Say it is taught</summary>
                      <div className="mt-2 grid max-w-[360px] justify-items-end gap-2 text-left text-[13px]">
                        <p>
                          Say a class has been taught {t.name}: its skills appear on that class&rsquo;s pages and can go on its
                          children&rsquo;s papers. No other class changes.
                        </p>
                        {waiting.map((c) => (
                          <Switch key={c.section} code={t.code} section={c.section} on label={`Taught in ${c.section}, as ${me}`} />
                        ))}
                      </div>
                    </details>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="note">
              {topics.some((t) => t.classes.length) ? "Every class has been taught every topic." : "No class has a child on the roll yet."}
            </p>
          )}
        </Panel>
        <section aria-label="Taught" id="taught" className="panel">
          <details>
            <summary className="panel-head cursor-pointer">
              <h2 className="text-[16px]">Taught</h2>
              <span className="fact text-[11px] text-basalt/55">
                {on.length} {on.length === 1 ? "topic" : "topics"} · open to say a class has not been taught one
              </span>
            </summary>
            <ul className="panel-body grid gap-3">
              {on.map((t) => (
                <li key={t.code} className="grid gap-1">
                  <b>{t.name}</b>
                  {t.classes
                    .filter((c) => c.taught)
                    .map((c) => (
                      <div key={c.section} className="grid gap-1 text-[13px]" data-class={c.section}>
                        <span className="flex flex-wrap items-center justify-between gap-3">
                          <span>
                            {c.section}: <span className="text-basalt/55">{said(c)}</span>
                          </span>
                          <Switch code={t.code} section={c.section} on={false} label={`Not taught in ${c.section}, as ${me}`} />
                        </span>
                        <Link className="text-basalt/70 underline" href={`/taught?skills=${t.code}&in=${c.section}#skills`}>
                          {c.skills.filter((k) => k.taught).length} of {c.skills.length} skills taught in {c.section} · say which →
                        </Link>
                      </div>
                    ))}
                </li>
              ))}
            </ul>
          </details>
        </section>
      </details>
    </div>
  );
}

/** Who said a class was taught: its own word, or the school's switch while no one has spoken for the class. */
function said(c: ClassTaught): string {
  if (c.own) return `said by ${c.by}${c.at ? `, ${dateWords(c.at)}` : ""}`;
  return c.by ? `as the school's switch, by ${c.by}` : "as the school's rows say";
}

function Switch({ code, skill, section, on, label }: { code: string; skill?: string; section: string; on: boolean; label: string }) {
  return (
    <form action={switchTopic}>
      <input type="hidden" name="code" value={code} />
      {skill ? <input type="hidden" name="skill" value={skill} /> : null}
      <input type="hidden" name="class" value={section} />
      <input type="hidden" name="taught" value={on ? "on" : "off"} />
      <button className={on ? "btn secondary" : "chip"} type="submit">
        {label}
      </button>
    </form>
  );
}
