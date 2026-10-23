import { DataTable } from "@/components/data-table";
import type { ClassLine, Person } from "@/lib/queries-staff";
import type { Column } from "@/lib/ux-rules";
import { setClasses } from "./actions";

function Edit({ person, classes }: { person: Person; classes: ClassLine[] }) {
  return (
    <details>
      <summary className="btn secondary cursor-pointer list-none text-[13px]">
        {person.classes.length
          ? person.classes.join(", ")
          : "No class yet: choose"}
      </summary>
      <form action={setClasses} className="mt-2 grid gap-2">
        <input type="hidden" name="email" value={person.email} />
        <fieldset className="flex flex-wrap gap-x-4 gap-y-1">
          <legend className="sr-only">Classes {person.name} teaches</legend>
          {classes.map((c) => (
            <label
              key={c.section}
              className="flex items-center gap-2 text-[14px]"
            >
              <input
                type="checkbox"
                name="class"
                value={c.section}
                defaultChecked={person.classes.includes(c.section)}
              />
              {c.section}
            </label>
          ))}
        </fieldset>
        <button type="submit" className="btn w-fit">
          Save the classes
        </button>
      </form>
    </details>
  );
}

export function StaffTable({
  people,
  classes,
  page,
  pageHref,
}: {
  people: Person[];
  classes: ClassLine[];
  page: number;
  pageHref: (page: number) => string;
}) {
  const columns: Column<Person>[] = [
    {
      key: "name",
      label: "Person",
      width: "14rem",
      keep: true,
      value: (p) => p.name,
      cell: (p) => (
        <>
          <div>{p.name}</div>
          <div className="text-[12px] text-basalt/60">{p.email}</div>
        </>
      ),
    },
    {
      key: "role",
      label: "Role",
      width: "9rem",
      keep: true,
      value: (p) => p.role,
    },
    {
      key: "classes",
      label: "Classes they teach",
      keep: true,
      value: (p) => p.classes.join(", "),
      cell: (p) => <Edit person={p} classes={classes} />,
    },
  ];
  return (
    <DataTable
      label="Staff"
      columns={columns}
      rows={people}
      rowKey={(p) => p.email}
      more={{ page, href: pageHref }}
      extras={{ attrs: (p) => ({ "data-person": p.email }) }}
    />
  );
}
