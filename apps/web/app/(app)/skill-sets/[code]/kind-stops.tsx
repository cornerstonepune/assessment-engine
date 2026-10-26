import Link from "@/components/link";
import { DataTable } from "@/components/data-table";
import { Panel, Notice } from "@/components/shell";
import { StatusChip } from "@/components/status-chip";
import { engineGet } from "@/lib/engine";
import type { WaysRow } from "@/lib/queries-skills";
import { startKind, stopKind } from "./stop-actions";

// An educator stops a kind of question at a level, or at every level, and can use it again (goals/gen_retire_a_kind.yaml).
// Nimish, 2026-10-26: "They should be able to delete those kinds of questions from the bank itself." Nothing is deleted:
// no new paper draws it, and every past paper and answer stays as it is. Before anything changes, the page says what it
// touches (the engine counts it, `GET /skill/{code}/kind/touches`), and the educator confirms.

type Row = { level: string; kind: string; words: string; stopped: boolean };
type Touches = { levels: string[]; questions: number; papers: number; withdraw: string[] };

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export async function KindStops({ code, ways, levels, q, mayChange }: {
  code: string;
  ways: WaysRow[];
  levels: string[];
  /** the page's address: the stop being confirmed (`stop=<level or all>~<kind>`), and the table's page (`kinds`) */
  q: Record<string, string | undefined>;
  mayChange: boolean;
}) {
  const rows: Row[] = levels.flatMap((level) =>
    ways.filter((w) => w.levels.includes(level)).map((w) => ({ level, kind: w.code, words: w.words, stopped: w.stopped.includes(level) })),
  );
  if (!rows.length) return null;
  const [at, kind] = (q.stop ?? "").split("~");
  const page = Math.max(1, Number(q.kinds) || 1);
  const asked = mayChange ? rows.find((r) => r.kind === kind && (at === "all" || r.level === at) && !r.stopped) : undefined;
  return (
    <Panel id="stop-kinds" title="Kinds of question in use" aside="a stopped kind is drawn by no new paper; past papers keep theirs">
      {asked ? <Confirm code={code} level={at === "all" ? null : at} kind={asked.kind} words={asked.words} /> : null}
      <DataTable
        label="Kinds of question in use"
        rowKey={(r) => `${r.level}~${r.kind}`}
        rows={rows}
        more={{ page, href: (n: number) => `/skill-sets/${code}?kinds=${n}#stop-kinds` }}
        extras={{ attrs: (r) => ({ "data-kind": r.kind, "data-level": r.level }) }}
        columns={[
          { key: "level", label: "Level", width: "7rem", value: (r) => r.level },
          { key: "kind", label: "Kind of question", value: (r) => r.words },
          { key: "state", label: "Now", status: true, width: "9rem", value: (r) => (r.stopped ? "stopped" : "in use"),
            cell: (r) => <StatusChip state={r.stopped ? "stopped" : "inUse"} /> },
          ...(mayChange
            ? [{ key: "do", label: "", width: "16rem", keep: true, value: () => "do",
                 cell: (r: Row) => r.stopped ? (
                   <form action={startKind}>
                     <input type="hidden" name="code" value={code} />
                     <input type="hidden" name="level" value={r.level} />
                     <input type="hidden" name="kind" value={r.kind} />
                     <button className="btn" type="submit" aria-label={`Use “${r.words}” again at ${r.level}`}>Use it again</button>
                   </form>
                 ) : (
                   <Link href={`/skill-sets/${code}?stop=${r.level}~${r.kind}#stop-kinds`} aria-label={`Stop using “${r.words}” at ${r.level}`}>
                     Stop using this kind of question
                   </Link>
                 ) }]
            : []),
        ]}
      />
    </Panel>
  );
}

/** What a stop touches, said before it is made; the educator confirms or keeps it. */
async function Confirm({ code, level, kind, words }: { code: string; level: string | null; kind: string; words: string }) {
  const res = await engineGet(
    `/skill/${code}/kind/touches?kind=${encodeURIComponent(kind)}${level ? `&level=${encodeURIComponent(level)}` : ""}`,
  ).catch(() => null);
  if (!res?.ok) return <Notice tone="terracotta">The engine could not be reached, so nothing can be stopped just now.</Notice>;
  const t = (await res.json()) as Touches;
  const where = level ? `at ${level}` : `at every level (${t.levels.join(", ")})`;
  return (
    <div className="mb-4 grid gap-2 border border-bamboo/45 bg-bamboo/10 p-3 text-[13.5px]" data-confirm-stop={kind}>
      <strong>Stop using &ldquo;{words}&rdquo; {where}?</strong>
      <ul className="grid list-disc gap-1 pl-5">
        <li>{plural(t.questions, "question", "questions")} in the bank will not be drawn for any new paper. Nothing is deleted.</li>
        <li>
          {t.papers
            ? `${plural(t.papers, "past paper holds", "past papers hold")} them; ${t.papers === 1 ? "it stays as it is" : "they stay as they are"}, and every answer on ${t.papers === 1 ? "it" : "them"} keeps its meaning.`
            : "No past paper holds them."}
        </li>
        {t.withdraw.length ? (
          <li data-withdraw={t.withdraw.join(" ")}>
            {plural(t.withdraw.length, "paper is", "papers are")} approved but not yet given ({t.withdraw.join(", ")}):{" "}
            {t.withdraw.length === 1 ? "it goes" : "they go"} back for approval, unchanged.
          </li>
        ) : null}
        <li>
          {t.levels.join(", ")} {t.levels.length === 1 ? "waits" : "wait"} for approval again. Until {t.levels.join(", ")}{" "}
          {t.levels.length === 1 ? "is" : "are"} approved again, no new paper is drawn from {t.levels.length === 1 ? "it" : "them"}.
          You can use the kind again at any time.
        </li>
      </ul>
      <div className="flex flex-wrap items-center gap-3">
        <form action={stopKind}>
          <input type="hidden" name="code" value={code} />
          <input type="hidden" name="level" value={level ?? "all"} />
          <input type="hidden" name="kind" value={kind} />
          <button className="btn" type="submit">Stop using this kind of question</button>
        </form>
        {level ? <Link href={`/skill-sets/${code}?stop=all~${kind}#stop-kinds`}>Stop it at every level instead</Link> : null}
        <Link href={`/skill-sets/${code}#stop-kinds`}>Keep using it</Link>
      </div>
    </div>
  );
}
