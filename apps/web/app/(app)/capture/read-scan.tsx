import { Panel } from "@/components/shell";
import type { Scan } from "@/lib/queries-scans";
import { readScan } from "./actions";
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
        <button type="submit" className="btn">
          Read it
        </button>
      </form>
      <p className="mt-2 text-[13px] text-ink-soft">
        {said ?? "Every page is sorted by the code printed on it and read in its boxes; every answer waits here for a person. A copy printed without a child's code is listed, not guessed."}
      </p>
      {scans.length ? (
        <ul aria-label="Scans read last" className="mt-3 grid gap-2 border-t border-line pt-3 text-[13px]">
          {scans.map((s) => (
            <li key={s.id} className="min-w-0">
              <p>
                <strong>{s.file}</strong> · {s.when} · {found(s)}
              </p>
              {s.noCode.length ? (
                <p className="text-terracotta">
                  No code could be read on {s.noCode.length === 1 ? "page" : "pages"} {s.noCode.join(", ")}: not guessed — photograph{" "}
                  {s.noCode.length === 1 ? "it" : "them"} again with the code in view.
                </p>
              ) : null}
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
