import { notFound } from "next/navigation";
import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { FilterBar, type Filter } from "@/components/filter-bar";
import { PageShell } from "@/components/page-shell";
import { Notice, Panel } from "@/components/shell";
import { StatusChip, type State } from "@/components/status-chip";
import { NotYours } from "@/components/not-yours";
import { requireStaff } from "@/lib/auth";
import { isMine, paperSection, reachOf } from "@/lib/scope";
import { EngineDown, engineGet } from "@/lib/engine";
import { staffList } from "@/lib/queries";
import { ApproveButton, Printed, RemoveButton, SeeIt, type Q, type Review } from "./parts";

// A child's paper before it prints (goals/paper_review_add_remove.yaml). Nimish, 2026-10-27: "When a teacher generates
// an assessment, they should see a page where they can look at the actual questions, and that should have an add/remove
// button". Its questions in order, each drawn as it prints, Remove on each, and the bank's dropdowns to add one. An edit
// makes the paper again with a new code (the engine's `edit_paper`), so the page moves to the new one.

type Props = { params: Promise<{ qr: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> };
type Bank = { topics: { code: string; name: string }[]; skills: { code: string; name: string }[]; levels: { code: string }[]; kinds: { code: string; words: string }[]; questions: Q[] };

const STATE: Record<Review["state"], [State, string]> = {
  waiting: ["toApprove", "waiting for approval"],
  approved: ["approved", "approved, not printed yet"],
  printed: ["printed", "printed"],
  replaced: ["replaced", "replaced by a newer one"],
};

async function read<T>(path: Parameters<typeof engineGet>[0]): Promise<T | string> {
  try {
    const res = await engineGet(path);
    if (res.status === 404) notFound();
    return res.ok ? ((await res.json()) as T) : `The engine could not show this paper (${res.status}).`;
  } catch (e) {
    return e instanceof EngineDown ? e.message : "The engine could not show this paper.";
  }
}

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || undefined;
const short = (s: string) => (s.length > 70 ? `${s.slice(0, 68)}…` : s);

export default async function ReviewPage({ params, searchParams }: Props) {
  const me = await requireStaff();
  const { qr } = await params;
  if (!/^CS[0-9A-F]{6}$/.test(qr)) notFound();
  if (!isMine(reachOf(me), await paperSection({ qr }))) return <NotYours what="This paper's class" />;
  const sp = await searchParams;
  const [topic, skill, level, kind, pick] = ["topic", "skill", "level", "kind", "q"].map((k) => one(sp[k]));
  const r = await read<Review>(`/paper/${qr}/review`);
  const here = `/papers/review/${qr}`;
  if (typeof r === "string")
    return (
      <PageShell stage="Assessments" title="Review a paper" purpose="A paper's questions before it prints." action={null} next={{ href: "/papers", label: "Assessments" }}>
        <p className="note">{r}</p>
      </PageShell>
    );
  const editable = !r.why_not;
  const q = new URLSearchParams(Object.entries({ topic, skill, level, kind }).filter((e): e is [string, string] => !!e[1]));
  const bank = editable ? await read<Bank>(`/paper/${qr}/bank?${q}`) : null;
  const b = typeof bank === "string" || !bank ? null : bank;
  const valid = <T,>(v: string | undefined, rows: T[] | undefined, key: (t: T) => string) => (v && rows?.some((x) => key(x) === v) ? v : undefined);
  const chosen = b?.questions.find((x) => x.id === pick);
  const filters: Filter[] = b
    ? [
        { name: "topic", label: "Topic", all: "Choose a topic", value: valid(topic, b.topics, (t) => t.code), options: b.topics.map((t) => [t.code, t.name] as const) },
        ...(topic ? [{ name: "skill", label: "Skill", all: "Choose a skill", value: valid(skill, b.skills, (s) => s.code), options: b.skills.map((s) => [s.code, s.name] as const) }] : []),
        ...(skill ? [{ name: "level", label: "Level", all: "Choose a level", value: valid(level, b.levels, (l) => l.code), options: b.levels.map((l) => [l.code, l.code] as const) }] : []),
        ...(level && b.kinds.length > 1 ? [{ name: "kind", label: "Kind of question", all: "Any kind", value: valid(kind, b.kinds, (k) => k.code), options: b.kinds.map((k) => [k.code, k.words] as const) }] : []),
        ...(level
          ? [{ name: "q", label: "Question", all: b.questions.length ? "Choose a question" : "None left at this level", value: chosen?.id, options: b.questions.map((x) => [x.id, short(x.text) + (x.days != null ? ` · given ${x.days} ${x.days === 1 ? "day" : "days"} ago` : "")] as const) }]
          : []),
      ]
    : [];
  const n = r.questions.length;
  const page = Math.max(1, Number(one(sp.p)) || 1);
  const done = one(sp.done);
  const gone = [sp.gone ?? []].flat();
  const action =
    r.state === "waiting" && editable ? (
      <ApproveButton r={r} />
    ) : r.state === "replaced" && r.newer ? (
      <Link href={`/papers/review/${r.newer}`} className="btn">Open the newer paper</Link>
    ) : r.state !== "waiting" ? (
      <a className="btn" href={`/api/papers/print?qr=${r.qr}`} target="_blank" rel="noreferrer">{r.state === "printed" ? "Print it again" : "Print it"}</a>
    ) : null;
  return (
    <PageShell
      stage="Assessments · review a paper"
      title={r.kind === "focus" ? "Review this home assessment" : "Review this paper"}
      purpose="Its questions as they will print. Remove one, or add one from the bank, before it prints."
      action={action}
      next={r.child_id ? { href: `/growth/${r.child_id}`, label: "Back to the child" } : { href: "/papers", label: "Assessments" }}
      details={{ href: `/worksheets/${r.qr}`, label: "Its answer key" }}
    >
      {done ? (
        <Notice tone="neem">
          {done === "approved" ? "Approved in your name: it may be printed now." : `${done === "add" ? "Added" : "Removed"}: the paper now holds ${one(sp.n)} questions.`}
          {gone.map((g) => ` ${g} now has no question.`).join("")}
          {one(sp.withdrew) ? " Its approval was withdrawn: it waits for approval again." : ""}
        </Notice>
      ) : null}
      {one(sp.error) ? <Notice tone="terracotta">{one(sp.error)}</Notice> : null}
      <section aria-label="Summary" data-summary className="mb-4 flex flex-wrap items-center gap-3 text-[14px]">
        <StatusChip state={STATE[r.state][0]} words={STATE[r.state][1]} />
        <span data-count-questions={n}>{`${n} ${n === 1 ? "question" : "questions"}`}</span>
        <span className="text-basalt/70">{r.covers.map((c) => `${c.name} · ${c.level} (${c.n})`).join(" · ")}</span>
        <span className="note">{`Code ${r.qr}`}</span>
      </section>
      {r.why_not ? <Notice tone="terracotta">{r.why_not}</Notice> : null}
      {r.state === "approved" && editable ? (
        <p className="note mb-3">Approved by {(await staffList()).find((x) => x.email === r.approved_by)?.name ?? r.approved_by}. Changing it withdraws the approval: it then waits for approval again.</p>
      ) : null}
      {n ? (
        <DataTable
          label="The paper's questions"
          rows={r.questions.map((x, i) => ({ ...x, n: i + 1 }))}
          rowKey={(x) => x.id}
          more={{ page, href: (p: number) => `${here}?p=${p}` }}
          extras={{ attrs: (x) => ({ "data-item": x.item_key, id: `q-${x.id}` }) }}
          columns={[
            { key: "n", label: "#", num: true, width: "3rem", value: (x) => x.n },
            { key: "q", label: "Question", value: (x) => x.text, cell: (x) => <Printed q={x} /> },
            { key: "skill", label: "Skill", width: "14rem", value: (x) => `${x.skill ?? x.skill_set} · ${x.topic_name ?? ""}` },
            { key: "level", label: "Level", width: "6rem", value: (x) => x.level },
            { key: "kind", label: "Kind", width: "10rem", value: (x) => x.kind_words },
            ...(editable ? [{ key: "remove", label: "", keep: true, width: "10rem", value: () => "Remove", cell: (x: Q) => <RemoveButton r={r} q={x} confirming={one(sp.confirm) === x.id} /> }] : []),
          ]}
        />
      ) : (
        <EmptyState>This paper holds no question.</EmptyState>
      )}
      {editable && b ? (
        <section aria-label="Add a question from the bank" className="mt-6">
          <h2 className="mb-2 text-[16px]">Add a question from the bank</h2>
          <FilterBar action={here} filters={filters} />
          {chosen ? <SeeIt r={r} q={chosen} /> : null}
        </section>
      ) : null}
      {r.pages ? (
        <details className="mt-5">
          <summary className="cursor-pointer text-[14px]">See it as it will print ({r.pages} {r.pages === 1 ? "page" : "pages"})</summary>
          <Panel title="The page as it prints">
            {Array.from({ length: r.pages }, (_, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={i} src={`/api/paper/${r.qr}/${i + 1}`} alt={`Page ${i + 1} of paper ${r.qr}`} className="mb-3 w-full border border-basalt/14 bg-white" loading="lazy" />
            ))}
          </Panel>
        </details>
      ) : null}
    </PageShell>
  );
}
