import { Notice } from "@/components/shell";
import { choosePage } from "../actions";
import type { CheckItem } from "@/lib/queries-read";

// What the engine worked out about a page (`GET /capture/{id}/proof`, w3_read/whose_paper.py): the screen shows it and
// decides nothing.
export type Proof = {
  scan: string;
  copy: number | null;
  copies: number | null;
  page: number;
  pages: number;
  code: string | null;
  printed_with: string;
  problem: { kind: string; text: string } | null;
  choice: "theirs" | "not_theirs" | null;
  chosen_by: string | null;
  may_confirm: boolean;
};

/** The page's own proof beside the crop: the whole page small with the crop outlined, the code printed on it, and which
 *  copy of the file and which page of the copy it is. */
export function PageProof({ a, p, next }: { a: CheckItem; p: Proof; next: string }) {
  const [l, t, r, b] = (a.box?.length === 4 && a.answer_state !== "not_found" ? a.box : [0, 0, 0, 0]).map(Number); // numeric comes as text
  return (
    <aside aria-label="Whose paper this page is" className="grid content-start gap-2 text-[13px]">
      <div className="relative w-[150px] border border-basalt/14 bg-chalk">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/api/scan/${a.capture_id}/${a.file_page}`} alt={`The whole page ${p.page} of ${a.first_name}'s paper`} className="block w-full" />
        {r > l ? (
          <span
            data-testid="crop-outline"
            className="absolute border-2 border-terracotta"
            style={{ left: `${l * 100}%`, top: `${t * 100}%`, width: `${(r - l) * 100}%`, height: `${(b - t) * 100}%` }}
          />
        ) : null}
      </div>
      <p>
        <span className="label">Paper</span> <strong className="fact">{p.printed_with}</strong>
      </p>
      <p>
        <span className="label">Code on this page</span>{" "}
        {p.code ? <strong className="fact">{p.code}</strong> : <span>none could be read</span>}
      </p>
      <p>
        {p.copy ? `Copy ${p.copy}${p.copies ? ` of ${p.copies}` : ""} in this file · ` : ""}page {p.page} of {p.pages}
      </p>
      {p.problem ? (
        <Notice tone="terracotta">
          <p>{p.problem.text}</p>
          {p.choice === "theirs" ? <p className="mt-1">{p.chosen_by} said this page is {a.first_name}&rsquo;s.</p> : null}
          {p.choice === "not_theirs" ? <p className="mt-1">{p.chosen_by} said this page is not {a.first_name}&rsquo;s. A person has to place it.</p> : null}
          <form action={choosePage} className="mt-2 flex flex-wrap gap-2">
            <input type="hidden" name="result_id" value={a.id} />
            <input type="hidden" name="capture_id" value={a.capture_id} />
            <input type="hidden" name="file_page" value={p.page} />
            <input type="hidden" name="next" value={next} />
            <button className="btn secondary" name="choice" value="theirs" type="submit">
              This page is {a.first_name}&rsquo;s
            </button>
            <button className="btn secondary" name="choice" value="not_theirs" type="submit">
              Not {a.first_name}&rsquo;s
            </button>
          </form>
        </Notice>
      ) : null}
    </aside>
  );
}
