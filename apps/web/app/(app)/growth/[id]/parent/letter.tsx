// The parent report as a parent reads it (goals/w4c-parent-report.yaml): a letter from the school, not a chart. The
// words are the engine's draft, held to the facts; the counts beside them are the facts themselves. The draft names
// the child "[child]"; the name is put in here, from pii, so no model ever saw it (rule 6).

export type Example = {
  question: string;
  wrote: string | null;
  right: string | number | null;
};
type Skill = {
  id: string;
  skill: string;
  can: string;
  right?: number;
  answered?: number;
  earlier?: string;
  recent?: string;
  ready_to_move_up?: boolean;
  not_yet?: string;
};
export type Facts = {
  grade: string;
  from: string;
  to: string;
  answers: number;
  can_do: Skill[];
  nearly: Skill[];
  improving: Skill[];
  working_on: {
    id: string;
    mistake: string;
    times: number;
    example: Example | null;
  }[];
  next: (Skill & { level: string; why?: string }) | null;
};
export type Draft = {
  summary: string;
  can_do: { id: string; sentence: string }[];
  working_on: { id: string; explanation: string }[];
  at_home: string[];
  next_at_school?: string;
};
export type Note = {
  id: string;
  facts: Facts;
  draft: Draft;
  approved_by: string | null;
  approved_at: string | null;
  written_at: string;
  stale: boolean;
};

const day = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

function Dots({ right, of }: { right: number; of: number }) {
  if (of > 12) return null;
  return (
    <span
      className="ml-2 inline-flex gap-[3px] align-middle"
      aria-hidden="true"
    >
      {Array.from({ length: of }, (_, i) => (
        <span
          key={i}
          className={`inline-block h-[7px] w-[7px] rounded-full ${i < right ? "bg-neem" : "border border-basalt/30"}`}
        />
      ))}
    </span>
  );
}

// What comes next is the engine's own choice, so it is said here from the facts, never written by the model: v5 was
// told a skill was secure and still wrote that the child "is still practising" it (goals/w4c-parent-report.yaml).
export function nextStep(next: Facts["next"], name: string): string | null {
  if (!next) return null;
  const skill = next.skill.toLowerCase();
  return next.why?.startsWith("secure")
    ? `${name} is secure at ${skill}, so the educator moves on to harder questions of it (${next.level}).`
    : `The educator gives ${name} more questions of ${skill}, at ${next.level}, until it is secure.`;
}

function Section({
  title,
  children,
  label,
}: {
  title: string;
  children: React.ReactNode;
  label: string;
}) {
  return (
    <section aria-label={label} className="mt-7 break-inside-avoid">
      <h2 className="mb-3 border-b border-basalt/15 pb-1 font-heading text-[18px]">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function Letter({
  note,
  name,
  section,
  approver,
}: {
  note: Note;
  name: string;
  section: string;
  approver: string | null;
}) {
  const put = (t: string) => t.replaceAll("[child]", name);
  const f = note.facts;
  const skills = Object.fromEntries(
    [...f.can_do, ...f.nearly, ...f.improving].map((s) => [s.id, s]),
  );
  const slips = Object.fromEntries(f.working_on.map((w) => [w.id, w]));
  return (
    <article
      data-testid="parent-report"
      className="relative mx-auto max-w-[800px] bg-chalk px-6 py-8 text-[15px] leading-[1.65] shadow-sm md:px-12 md:py-10 print:max-w-none print:shadow-none"
    >
      {note.approved_by ? null : (
        <p
          className="mb-6 border border-dashed border-terracotta/60 bg-terracotta/8 p-2 text-center text-[13px] text-terracotta"
          data-testid="draft-mark"
        >
          Draft — an educator checks and approves this before it goes to {name}
          &apos;s parents.
        </p>
      )}
      <header className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-basalt pb-4">
        <div>
          <div className="label !tracking-[0.12em]">
            Cornerstone School, Pune · Maths report
          </div>
          <h1 className="mt-2 font-heading text-[30px] leading-tight">
            {name}
          </h1>
          <div className="text-[13.5px] text-basalt/70">
            {f.grade} · {section}
          </div>
        </div>
        <div className="text-right text-[13px] text-basalt/70">
          {f.from === f.to ? day(f.from) : `${day(f.from)} – ${day(f.to)}`}
          <br />
          {f.answers} answers, each checked by an educator
        </div>
      </header>

      <Section title={`How ${name} is doing`} label="How they are doing">
        <p className="text-[16.5px] leading-[1.7]">{put(note.draft.summary)}</p>
      </Section>

      {note.draft.can_do.length ? (
        <Section title={`What ${name} can do`} label="What they can do">
          <ul className="grid gap-3">
            {note.draft.can_do.map((c) => {
              const s = skills[c.id];
              return (
                <li key={c.id} className="flex gap-3">
                  <span
                    className="mt-[2px] font-heading text-neem"
                    aria-hidden="true"
                  >
                    ✓
                  </span>
                  <div>
                    <div className="font-heading text-[15px]">
                      {s?.skill}
                      {s?.answered ? (
                        <Dots right={s.right ?? 0} of={s.answered} />
                      ) : null}
                      {s?.ready_to_move_up ? (
                        <span className="pill pill-neem ml-2 align-middle">
                          ready for the next step
                        </span>
                      ) : null}
                      {s?.not_yet ? (
                        <span className="pill pill-bamboo ml-2 align-middle">
                          nearly secure
                        </span>
                      ) : null}
                      {s?.recent ? (
                        <span className="pill pill-bamboo ml-2 align-middle">
                          improving
                        </span>
                      ) : null}
                    </div>
                    <div className="text-basalt/80">{put(c.sentence)}</div>
                    {s?.not_yet ? (
                      <div className="text-[13px] text-basalt/60">
                        Why not yet secure: {s.not_yet}.
                      </div>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </Section>
      ) : null}

      {note.draft.working_on.length ? (
        <Section
          title={`What ${name} is working on`}
          label="What they are working on"
        >
          <ul className="grid gap-4">
            {note.draft.working_on.map((w) => {
              const ex = slips[w.id]?.example;
              return (
                <li key={w.id}>
                  <p>{put(w.explanation)}</p>
                  {ex ? (
                    <div className="mt-2 inline-grid grid-cols-3 gap-[2px] text-center text-[13px]">
                      <div className="bg-lime px-4 py-2">
                        <div className="label">Question</div>
                        <div className="font-heading text-[15px]">
                          {ex.question}
                        </div>
                      </div>
                      <div className="bg-terracotta/10 px-4 py-2">
                        <div className="label">{name} wrote</div>
                        <div className="font-heading text-[15px] text-terracotta">
                          {ex.wrote ?? "—"}
                        </div>
                      </div>
                      <div className="bg-neem/10 px-4 py-2">
                        <div className="label">The answer</div>
                        <div className="font-heading text-[15px] text-neem">
                          {ex.right ?? "—"}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Section>
      ) : null}

      <Section title="How you can help at home" label="At home">
        <ol className="grid list-decimal gap-2 pl-5">
          {note.draft.at_home.map((a, i) => (
            <li key={i}>{put(a)}</li>
          ))}
        </ol>
      </Section>

      <Section title="Next at school" label="Next at school">
        <p>{nextStep(f.next, name) ?? put(note.draft.next_at_school ?? "")}</p>
      </Section>

      <footer className="mt-9 flex flex-wrap justify-between gap-3 border-t border-basalt/15 pt-3 text-[12.5px] text-basalt/65">
        <span>
          Written from {name}&apos;s own answers; every number here was counted,
          not estimated.
        </span>
        <span data-testid="approval">
          {note.approved_by
            ? `Approved by ${approver ?? note.approved_by} on ${day(note.approved_at!)}`
            : "Not yet approved"}
        </span>
      </footer>
    </article>
  );
}
