import "./school-tokens.css";
import { Suspense } from "react";
import { type MenuItem, ShellNav } from "./shell-nav";

// The shell of the school's own screens (D-075): white ground, the area's menu down the left (a tab bar at the foot of
// a phone), the page in the other ten of twelve columns, and the school's tokens loaded for this shell alone. An area
// moves in with one change: its layout renders <SchoolShell items={its menu} label={its name}>.
export function SchoolShell({ items, label, children }: { items: MenuItem[]; label: string; children: React.ReactNode }) {
  return (
    <div data-educator className="grid flex-1 grid-cols-12 gap-x-[var(--space-4)] bg-[var(--surface)] text-[length:var(--text-body)] text-[var(--text)] max-md:pb-[var(--space-7)] md:px-[var(--space-4)] md:pt-[var(--space-4)]">
      <aside className="col-span-2 max-md:hidden">
        <Suspense>
          <ShellNav as="side" items={items} label={label} />
        </Suspense>
      </aside>
      <div className="col-span-12 min-w-0 md:col-span-10">{children}</div>
      <div className="md:hidden">
        <Suspense>
          <ShellNav as="tabs" items={items} label={label} />
        </Suspense>
      </div>
    </div>
  );
}
