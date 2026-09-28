// The report card's sections (goals/u6-report-card.yaml). Every sentence is built from a counted fact — the engine's
// report (`w4_close/report.py`: strong, each named mistake with the child's own example and what the school does about
// it, the next area) and the skill map — so nothing on the card is guessed. Anything a parent reads says "educator".
import type { MapNode } from "@/lib/queries-report";
import { STATE_WORDS } from "@/lib/queries";

export type Example = {
  question: string;
  wrote: string | null;
  right: string | number | null;
};
export type Mistake = {
  mistake: string;
  name: string;
  hint: string | null;
  skill: string;
  times: number;
  example: Example | null;
};
export type Report = {
  strong: {
    skill_set: string | null;
    name: string;
    right: number;
    answered: number;
  }[];
  faulty: Mistake[];
  unexplained: { skill_code: string; skill: string; times: number }[];
  next: {
    skill_set: string;
    level: string;
    mistake: string | null;
    state: string;
  } | null;
};

const plural = (n: number, one: string, many = `${one}s`) =>
  `${n} ${n === 1 ? one : many}`;

export function Signals({ nodes }: { nodes: MapNode[] }) {
  const sum = (k: "right" | "wrong" | "wrong_working" | "blank") =>
    nodes.reduce((s, n) => s + n[k], 0);
  const parts = [
    ["right", sum("right"), "bg-neem"],
    ["wrong, with working", sum("wrong_working"), "bg-bamboo"],
    ["wrong", sum("wrong"), "bg-terracotta"],
    ["left blank", sum("blank"), "bg-monsoon"],
  ] as const;
  const total = parts.reduce((s, p) => s + p[1], 0);
  if (!total) return null;
  return (
    <section aria-label="Every answer" className="mb-5">
      <div className="flex h-4 w-full overflow-hidden rounded-sm bg-basalt/10">
        {parts.map(([w, n, bg]) =>
          n ? (
            <span
              key={w}
              className={bg}
              style={{ width: `${(n / total) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
        {parts.map(([w, n, bg]) => (
          <li key={w} data-signal={w} className="flex items-center gap-2">
            <span className={`inline-block h-3 w-3 rounded-sm ${bg}`} />
            <b>{n}</b> {w}
          </li>
        ))}
        <li className="text-basalt/60">of {total} answers</li>
      </ul>
    </section>
  );
}

/** What is going well, always at least one true thing: the skill sets the graph calls secure or ready to move up; then
 *  those four in five right that wait only for a second paper; then the habit of showing working; then the most right. */
export function GoingWell({
  name,
  report,
  nodes,
}: {
  name: string;
  report: Report;
  nodes: MapNode[];
}) {
  const strong = new Set(report.strong.map((s) => s.skill_set));
  const nearly = nodes.filter((n) => {
    const answered = n.right + n.wrong + n.wrong_working;
    return (
      !strong.has(n.code) &&
      n.state === "practising" &&
      answered >= 3 &&
      n.right / answered >= 0.8
    );
  });
  const wrong = nodes.reduce((s, n) => s + n.wrong + n.wrong_working, 0);
  const working = nodes.reduce((s, n) => s + n.wrong_working, 0);
  const best = [...nodes].sort((a, b) => b.right - a.right)[0];
  const items: { key: string; head: string; body: string }[] = [
    ...report.strong.map((s) => ({
      key: `s-${s.skill_set}-${s.name}`,
      head: s.name,
      body: `${s.right} of ${s.answered} right — ${nodes.find((n) => n.code === s.skill_set)?.state === "stretch_ready" ? STATE_WORDS.stretch_ready.words : STATE_WORDS.secure.words}.`,
    })),
    ...nearly.map((n) => ({
      key: `n-${n.code}`,
      head: n.name,
      body: `${n.right} of ${n.right + n.wrong + n.wrong_working} right — one more paper on it to call it secure.`,
    })),
  ];
  if (working)
    items.push({
      key: "working",
      head: "Shows working",
      body: `${name} showed working on ${working} of ${plural(wrong, "wrong answer")}, so the educator can see exactly which step slipped.`,
    });
  if (!items.length && best?.right)
    items.push({
      key: "best",
      head: best.name,
      body: `${plural(best.right, "right answer")} so far — the most of any skill set.`,
    });
  return (
    <ul className="grid gap-3" data-testid="going-well">
      {items.length ? (
        items.map((i) => (
          <li key={i.key} className="border-l-4 border-l-neem bg-neem/8 p-3">
            <div className="font-heading text-[15px]">{i.head}</div>
            <div className="mt-1 text-[13.5px] text-basalt/75">{i.body}</div>
          </li>
        ))
      ) : (
        <li className="text-[13.5px] text-basalt/60">
          Nothing signed off yet to show.
        </li>
      )}
    </ul>
  );
}

function ExampleCard({ e, name }: { e: Example; name: string }) {
  return (
    <div className="mt-2 grid grid-cols-3 gap-2 text-center text-[13px]">
      <div className="bg-chalk p-2">
        <div className="label mb-1">Question</div>
        <div className="font-heading text-[14px]">{e.question}</div>
      </div>
      <div className="bg-terracotta/10 p-2">
        <div className="label mb-1">{name} wrote</div>
        <div className="font-heading text-[16px] text-terracotta line-through decoration-1">
          {e.wrote ?? "—"}
        </div>
      </div>
      <div className="bg-neem/10 p-2">
        <div className="label mb-1">Answer</div>
        <div className="font-heading text-[16px] text-neem">
          {e.right ?? "—"}
        </div>
      </div>
    </div>
  );
}

export function WorkingOn({ name, report }: { name: string; report: Report }) {
  const unexplained = report.unexplained.reduce((s, u) => s + u.times, 0);
  if (!report.faulty.length && !unexplained)
    return (
      <p className="text-[13.5px] text-basalt/60">
        No mistake shows in the signed-off answers.
      </p>
    );
  return (
    <ul className="grid gap-3" data-testid="working-on">
      {report.faulty.slice(0, 4).map((f) => (
        <li
          key={f.mistake}
          data-mistake={f.mistake}
          className="border-l-4 border-l-terracotta bg-terracotta/6 p-3"
        >
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-heading text-[15px]">{f.name}</span>
            <span className="fact shrink-0 text-[12px] text-basalt/60">
              {plural(f.times, "time")}
            </span>
          </div>
          {f.example ? <ExampleCard e={f.example} name={name} /> : null}
        </li>
      ))}
      {unexplained ? (
        <li
          className="border-l-4 border-l-monsoon bg-monsoon/8 p-3 text-[13.5px]"
          data-testid="unexplained"
        >
          {plural(unexplained, "other wrong answer")} (
          {report.unexplained.map((u) => `${u.skill} ${u.times}`).join(", ")})
          match no named mistake yet; the educator looks at each one.
        </li>
      ) : null}
    </ul>
  );
}

/** What happens next, for each reader: the educator's reteach from the school's own repair hint for each mistake and
 *  the home paper's area; the parent's from the child's own questions, in plain words. */
export function NextSteps({
  id,
  name,
  report,
  nodes,
}: {
  id: string;
  name: string;
  report: Report;
  nodes: MapNode[];
}) {
  const next =
    report.next && nodes.find((n) => n.code === report.next!.skill_set);
  const blanks = nodes.reduce((s, n) => s + n.blank, 0);
  const unexplained = report.unexplained.reduce((s, u) => s + u.times, 0);
  const strong = report.strong[0]?.name;
  const educator = [
    ...report.faulty
      .filter((f) => f.hint)
      .slice(0, 3)
      .map((f) => ({ key: f.mistake, head: f.name, body: f.hint! })),
    ...(next
      ? [
          {
            key: "next",
            head: "Home assessment",
            body: `${next.name}, at ${report.next!.level} — made for ${name} from these answers; approve it on ${name}'s page.`,
          },
        ]
      : []),
    ...(unexplained
      ? [
          {
            key: "unexplained",
            head: "Look again",
            body: `${plural(unexplained, "wrong answer")} no named mistake explains — on ${name}'s page.`,
          },
        ]
      : []),
  ];
  const parent = [
    ...(next
      ? [
          {
            key: "next",
            body: `This week ${name} brings home a short paper on ${next.name.toLowerCase()}. Sit together for ten minutes and ask ${name} to say each step out loud.`,
          },
        ]
      : []),
    ...report.faulty
      .filter((f) => f.example?.question && f.example.right != null)
      .slice(0, 2)
      .map((f) => ({
        key: f.mistake,
        body: `Try this one together: ${f.example!.question} Last time ${name} wrote ${f.example!.wrote ?? "nothing"}; the answer is ${f.example!.right}. Ask ${name} to work it again and check it.`,
      })),
    ...(blanks >= 2
      ? [
          {
            key: "blank",
            body: `${name} left ${plural(blanks, "question")} blank. Encourage a try at every question — a try with working shows the educator where to help.`,
          },
        ]
      : []),
    ...(strong
      ? [
          {
            key: "praise",
            body: `Praise the work on ${strong.toLowerCase()}: it is secure.`,
          },
        ]
      : []),
  ];
  return (
    <div className="grid gap-[18px] md:grid-cols-2">
      <section aria-label="In class" className="panel p-4">
        <h3 className="mb-3 text-[15px]">In class — for the educator</h3>
        <ol className="grid list-decimal gap-3 pl-5 text-[13.5px]">
          {educator.map((e) => (
            <li key={e.key}>
              <b>{e.head}:</b> {e.body}
            </li>
          ))}
        </ol>
        <a
          href={`/growth/${id}`}
          className="mt-3 inline-block text-[12.5px] underline print:hidden"
        >
          {name}&apos;s page →
        </a>
      </section>
      <section aria-label="At home" className="panel p-4">
        <h3 className="mb-3 text-[15px]">At home — for parents</h3>
        <ol className="grid list-decimal gap-3 pl-5 text-[13.5px]">
          {parent.map((p) => (
            <li key={p.key}>{p.body}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
