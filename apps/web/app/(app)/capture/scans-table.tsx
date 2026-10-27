import { DataTable } from "@/components/data-table";
import { StatusChip, type State } from "@/components/status-chip";
import type { Scan } from "@/lib/queries-scans";
import type { Column } from "@/lib/ux-rules";
import { givePage, readAgain } from "./actions";

/** What a file's run came to: still being read, stopped, waiting on a person (a page with no code, a page or a copy it
 *  lacks, an answer to check) or read whole. */
const stateOf = (s: Scan): State =>
  s.status === "running" ? "waiting" : s.status === "error" ? "unreadable" : s.noCode.length || s.lines.length || s.waiting ? "toCheck" : "done";

// The files read last (goals/n8-upload-on-marking.yaml, goals/uxn6-upload-papers.yaml): one table, a file a row, what it
// held and came to in columns, its state as a chip, "Read again" at the end; under a row, what a person must act on: the
// pages given to a child, the pages with no code (goals/ux9a-no-guessed-pages.yaml) and what the file lacks, by class and
// roll number, never a name (goals/l11-a-scan-is-read-whole.yaml).
export function ScansTable({ scans, from }: { scans: Scan[]; from: string }) {
  const columns: Column<Scan>[] = [
    { key: "file", label: "File", value: (s) => s.file, cell: (s) => <strong className="break-all">{s.file}</strong> },
    { key: "when", label: "Read on", width: "10rem", value: (s) => s.when },
    { key: "pages", label: "Pages", num: true, width: "5rem", value: (s) => s.pages, cell: (s) => (s.pages === null ? null : `${s.pages} ${s.pages === 1 ? "page" : "pages"}`) },
    { key: "copies", label: "Copies read", num: true, width: "6.5rem", value: (s) => s.read },
    { key: "answers", label: "Answers", num: true, width: "6rem", value: (s) => s.answers },
    { key: "engine", label: "Settled by the engine", num: true, width: "7rem", value: (s) => s.engine },
    { key: "person", label: "Checked by a person", num: true, width: "7rem", value: (s) => s.person },
    { key: "waiting", label: "Waiting", num: true, width: "5.5rem", value: (s) => s.waiting },
    { key: "state", label: "Status", status: true, width: "10rem", value: (s) => stateOf(s), cell: (s) => <StatusChip state={stateOf(s)} words={s.status === "running" ? "reading now" : s.status === "error" ? "reading stopped" : undefined} /> },
    {
      key: "again",
      label: "",
      width: "8rem",
      keep: true,
      value: (s) => s.id,
      cell: (s) =>
        s.status !== "running" ? (
          <form action={readAgain} aria-label={`Read ${s.file} again`}>
            <input type="hidden" name="run" value={s.id} />
            <input type="hidden" name="from" value={from} />
            <button type="submit" className="btn secondary">
              Read again
            </button>
          </form>
        ) : null,
    },
  ];
  return (
    <DataTable
      label="Scans read last"
      columns={columns}
      rows={scans}
      rowKey={(s) => s.id}
      more={{ page: 1, href: () => from }}
      extras={{ expand: (s) => <Detail s={s} from={from} /> }}
    />
  );
}

/** What waits on a person in one file, and its other readings, or nothing (the row under it is then not drawn). */
function Detail({ s, from }: { s: Scan; from: string }) {
  const attempts = s.attempts.length ? <Attempts scan={s} /> : null;
  if (s.status === "error")
    return (
      <div className="grid gap-1 text-[13px]">
        <p className="text-terracotta">The reading stopped: {s.error ?? ""}</p>
        {attempts}
      </div>
    );
  if (!s.given.length && !s.noCode.length && !s.lines.length) return attempts;
  return (
    <div className="grid gap-1 text-[13px]">
      {attempts}
      {s.given.length ? (
        <p>
          {s.given.map((g) => `Page ${g.page} given to ${g.who}`).join("; ")}
          {s.status === "running" ? ": reading it now." : "."}
        </p>
      ) : null}
      {s.noCode.length ? <WaitingPages scan={s} from={from} /> : null}
      {s.lines.length ? (
        <ul aria-label={`What ${s.file} lacks`} className="ml-5 list-disc text-terracotta">
          {s.lines.map((l, i) => (
            <li key={i}>
              {l.who}: {l.said}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** A file read more than once is one line (Nimish, 2026-10-26: five "reading stopped" lines for one file): its other
 *  readings, newest first, folded under it, each when and how it ended. */
function Attempts({ scan: s }: { scan: Scan }) {
  const said = (a: Scan["attempts"][number]) => (a.status === "running" ? "reading now" : a.status === "ok" ? "read" : `stopped: ${a.error ?? ""}`);
  return (
    <details>
      <summary className="cursor-pointer">
        Read {s.attempts.length + 1} times; the {s.attempts.length === 1 ? "other reading" : `other ${s.attempts.length} readings`}
      </summary>
      <ul aria-label={`Other readings of ${s.file}`} className="ml-5 list-disc">
        {s.attempts.map((a, i) => (
          <li key={i}>
            {a.when}: {said(a)}
          </li>
        ))}
      </ul>
    </details>
  );
}

/** The pages of a file on which no code could be read (goals/ux9a-no-guessed-pages.yaml). Nimish, 2026-10-22: "yes, stop
 *  guessing." Such a page is read as no child's until a person says whose it is: each is shown small, with a button for
 *  each child whose own paper is in the file, a copy short of a page first, the rest folded. One tap, and the file is
 *  read again with the page as that child's. */
function WaitingPages({ scan: s, from }: { scan: Scan; from: string }) {
  const short = s.owners.filter((o) => o.short);
  const rest = s.owners.filter((o) => !o.short);
  return (
    <ul aria-label={`Pages of ${s.file} waiting for their child`} className="mt-1 grid gap-2">
      {s.noCode.map((n) => (
        <li key={n} className="flex flex-wrap items-start gap-3">
          <a href={`/api/scan-run/${s.id}/${n}`} target="_blank" rel="noreferrer" aria-label={`See page ${n}`}>
            {/* eslint-disable-next-line @next/next/no-img-element -- a scan the engine draws, never a static asset */}
            <img src={`/api/scan-run/${s.id}/${n}`} alt={`Page ${n} of ${s.file}`} width={72} className="border border-line" />
          </a>
          <div className="min-w-0 flex-1">
            <p className="text-terracotta">
              Page {n}: no code could be read on it, so it is not read until you say whose it is.
              {s.owners.length ? "" : " No child's own paper is in this file: photograph it again with the code in view."}
            </p>
            {s.owners.length && s.status !== "running" ? (
              <form action={givePage} aria-label={`Whose is page ${n}?`} className="mt-1 flex flex-wrap items-center gap-2">
                <input type="hidden" name="run" value={s.id} />
                <input type="hidden" name="page" value={n} />
                <input type="hidden" name="from" value={from} />
                {(short.length ? short : rest).map((o) => (
                  <button key={o.id} type="submit" name="child" value={o.id} className="btn secondary">
                    {o.who}
                    {o.short ? " (a page short)" : ""}
                  </button>
                ))}
                {short.length && rest.length ? (
                  <details>
                    <summary className="cursor-pointer text-[13px]">Another child in this file</summary>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {rest.map((o) => (
                        <button key={o.id} type="submit" name="child" value={o.id} className="btn secondary">
                          {o.who}
                        </button>
                      ))}
                    </div>
                  </details>
                ) : null}
              </form>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
