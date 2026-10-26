import { addPerson } from "./actions";

// Add a member of staff (goals/auth-email-password.yaml). No password field: the person is emailed a link and sets
// their own, so nobody here types or sees it. Their classes and subjects are chosen afterwards, on their own row.
export function AddPerson({ roles }: { roles: string[] }) {
  return (
    <details className="mt-4">
      <summary className="btn secondary w-fit cursor-pointer list-none text-[13px]">Add a member of staff</summary>
      <form action={addPerson} className="mt-3 grid max-w-[640px] gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="field">
          <span className="label">Name</span>
          <input className="input" type="text" name="name" required />
        </label>
        <label className="field">
          <span className="label">School email</span>
          <input className="input" type="email" name="email" required />
        </label>
        <label className="field">
          <span className="label">Role</span>
          <select className="input" name="role" defaultValue="educator">
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <button className="btn md:col-start-3" type="submit">
          Add and send a link
        </button>
      </form>
    </details>
  );
}
