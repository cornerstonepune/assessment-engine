import { Panel } from "@/components/shell";
import type { Scan } from "@/lib/queries-scans";
import { givePage, readAgain, readScan } from "./actions";
import { UploadScans } from "./upload-scans";

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** What a file's run came to (goals/n8-upload-on-marking.yaml): its pages, its copies and children, and once read, its
 *  answers settled by the engine, checked by a person, and waiting for one. */
function found(s: Scan): string {
  const pages = s.pages === null ? "" : `${plural(s.pages, "page")}, `;
  if (s.status === "running") return `${pages}reading now`;
  if (s.status === "error") return `${pages}the reading stopped: ${s.error ?? ""}`;
  return (
    `${pages}${plural(s.copies, "copy", "copies")} found for ${plural(s.children, "child", "children")} · ` +
    `${plural(s.read, "copy", "copies")} read, ${plural(s.answers, "answer")}: ${s.engine} settled by the engine, ` +
    `${s.person ? `${s.person} checked by a person, ` : ""}${s.waiting} waiting for a person`
  );
}

// Scans in (N8): put in from this page, or by a Drive link the engine fetches. Either way the engine reads the file after
// it has answered, so the notice says it has started; the papers appear above as they are read. What the engine would
// not take, in its own words. Under it, the last files read, what each held and came to, and what each lacks: a page
// with no code, a page not in the file, a page in it twice, a copy not read (goals/l11-a-scan-is-read-whole.yaml).
export function ReadScan({ from, read, why, pages, scans = [] }: { from: "/papers" | "/capture"; read?: string; why?: string; pages?: string; scans?: Scan[] }) {
  const said = {
    started: `Reading ${Number(pages) || ""} pages. The papers appear here as they are read — a minute or two.`,
    refused: `The engine would not take that: ${why ?? ""}`,
    "not-a-link": "Paste the link to the scan on Google Drive (drive.google.com/…).",
    engine: "The engine is not answering; nothing was read.",
    given: `Page ${Number(pages) || ""} is being read now as the paper of the child you gave it to.`,
    again: `Reading ${Number(pages) || ""} pages again. Answers a person has checked stay as they left them; the rest are read anew — a minute or two.`,
  }[read ?? ""];
  return (
    <Panel title="Read a scan" label="Read a scan" id="read-scan">
      <UploadScans reading={scans.some((s) => s.status === "running")} />
      <p className="mb-1 text-[13px] text-ink-soft">Or paste the link to a scan on Google Drive:</p>
      <form action={readScan} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="from" value={from} />
        <input
          type="url"
          name="url"
          required
          placeholder="https://drive.google.com/file/d/…/view"
          aria-label="Link to the scan on Google Drive"
          className="min-w-0 flex-1 rounded border border-line bg-chalk px-3 py-2 text-[14px]"
        />
        <button type="submit" className="btn secondary">
          Read it
        </button>
      </form>
      <p className="mt-2 text-[13px] text-ink-soft">
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code, or a page whose code cannot be read, is listed, never guessed."}
      </p>
      {scans.length ? (
        <ul aria-label="Scans read last" className="mt-3 grid gap-2 border-t border-line pt-3 text-[13px]">
          {scans.map((s) => (
            <li key={s.id} className="min-w-0">
              <p>
                <strong>{s.file}</strong> · {s.when} · {found(s)}
              </p>
              {s.status !== "running" ? (
                <form action={readAgain} aria-label={`Read ${s.file} again`} className="mt-1">
                  <input type="hidden" name="run" value={s.id} />
                  <input type="hidden" name="from" value={from} />
                  <button type="submit" className="btn secondary">
                    Read again
                  </button>
                </form>
              ) : null}
              {s.given.length ? (
                <p>
                  {s.given.map((g) => `Page ${g.page} given to ${g.who}`).join("; ")}
                  {s.status === "running" ? ": reading it now." : "."}
                </p>
              ) : null}
              {s.noCode.length ? <WaitingPages scan={s} from={from} /> : null}
              {s.lines.length ? (
                <ul aria-label={`What ${s.file} lacks`} className="ml-5 mt-1 list-disc text-terracotta">
                  {s.lines.map((l, i) => (
                    <li key={i}>
                      {l.who}: {l.said}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </Panel>
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
