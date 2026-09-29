// An educator's own words for the report (goals/w4c-parent-report.yaml): every part of the draft, editable, the
// child's name shown where the draft says [child] and turned back into [child] on saving, so no name is stored
// (rule 6). The engine holds the edit to the same facts as the model's words, and keeps it as a new version.
import { editParentReport } from "../../actions";
import type { Note } from "./letter";

const box =
  "mt-1 w-full rounded border border-basalt/25 bg-chalk p-2 text-[14.5px] leading-[1.55]";

export function EditForm({
  note,
  name,
  id,
}: {
  note: Note;
  name: string;
  id: string;
}) {
  const put = (t: string) => t.replaceAll("[child]", name);
  const f = note.facts;
  const skill = Object.fromEntries(
    [...f.can_do, ...f.nearly, ...f.improving].map((s) => [s.id, s.skill]),
  );
  const slip = Object.fromEntries(f.working_on.map((w) => [w.id, w.mistake]));
  const home = [...note.draft.at_home, "", ""].slice(0, 3);
  return (
    <form
      action={editParentReport}
      data-testid="edit-report"
      className="mx-auto grid max-w-[800px] gap-5 bg-chalk px-6 py-8 text-[14px] shadow-sm md:px-12"
    >
      <input type="hidden" name="child_id" value={id} />
      <input type="hidden" name="note_id" value={note.id} />
      <input type="hidden" name="name" value={name} />
      <label>
        <span className="font-heading text-[16px]">How {name} is doing</span>
        <textarea
          name="summary"
          rows={5}
          className={box}
          defaultValue={put(note.draft.summary)}
        />
      </label>
      {note.draft.can_do.map((c) => (
        <label key={c.id}>
          <span className="font-heading">{skill[c.id] ?? "A skill"}</span>
          <input type="hidden" name="can_do_id" value={c.id} />
          <textarea
            name="can_do_text"
            rows={2}
            className={box}
            defaultValue={put(c.sentence)}
          />
        </label>
      ))}
      {note.draft.working_on.map((w) => (
        <label key={w.id}>
          <span className="font-heading">
            Working on: {slip[w.id] ?? "a mistake"}
          </span>
          <input type="hidden" name="working_id" value={w.id} />
          <textarea
            name="working_text"
            rows={3}
            className={box}
            defaultValue={put(w.explanation)}
          />
        </label>
      ))}
      <fieldset>
        <legend className="font-heading text-[16px]">
          How you can help at home
        </legend>
        {home.map((a, i) => (
          <textarea
            key={i}
            name="at_home"
            rows={2}
            className={box}
            defaultValue={put(a)}
            placeholder="Leave empty to leave out"
          />
        ))}
      </fieldset>
      <p className="text-[13px] text-basalt/65">
        Your words are checked against {name}&apos;s answers as the draft was:
        no number the answers do not hold, no other child&apos;s name, the
        school&apos;s own words. Saving keeps the earlier draft.
      </p>
      <div className="flex gap-2">
        <button
          type="submit"
          className="chip cursor-pointer !border-neem !bg-neem !text-chalk"
        >
          Save my version
        </button>
        <a href={`/growth/${id}/parent`} className="chip">
          Cancel
        </a>
      </div>
    </form>
  );
}
