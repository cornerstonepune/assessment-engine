import { Notice } from "@/components/shell";
import { readScan } from "../capture/actions";
import { UploadScans } from "../capture/upload-scans";

// Read an assessment (goals/asm_assessments_page.yaml): one drop zone, the Google Drive link, and one button. What the
// engine said about the last file is one line above it; what each file came to is on its assessment's row.
export function ReadBox({ read, why, pages, reading }: { read?: string; why?: string; pages?: string; reading: boolean }) {
  const said = {
    started: `Reading ${Number(pages) || ""} pages. They appear in the list as they are read — a minute or two.`,
    refused: `The engine would not take that: ${why ?? ""}`,
    "not-a-link": "Paste the link to the scan on Google Drive (drive.google.com/…).",
    engine: "The engine is not answering; nothing was read.",
    given: `Page ${Number(pages) || ""} is being read now as the paper of the child you gave it to.`,
    again: `Reading ${Number(pages) || ""} pages again. Answers a person has checked stay as they left them.`,
  }[read ?? ""];
  return (
    <section id="read-box" aria-label="Read an assessment" className="panel flex min-w-0 flex-col gap-2 p-4">
      <h2 className="label">Read an assessment</h2>
      {said ? <Notice tone={read === "started" || read === "given" || read === "again" ? "neem" : "terracotta"}>{said}</Notice> : null}
      <UploadScans reading={reading} />
      <form action={readScan} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="from" value="/papers" />
        <input
          type="url"
          name="url"
          required
          placeholder="Or a Google Drive link: https://drive.google.com/file/d/…"
          aria-label="Link to the scan on Google Drive"
          className="min-w-0 flex-1 rounded border border-line bg-chalk px-3 py-2 text-[14px]"
        />
        <button type="submit" className="btn secondary">
          Read it
        </button>
      </form>
    </section>
  );
}
