import { Suspense } from "react";
import { EducatorNav } from "@/components/educator/nav";

// The K2 educator's screens (M1-09, D-075): white ground, her menu down the left (a tab bar at the foot of a phone),
// the page in the other ten of twelve columns. Every block under it reads design-system/tokens.css and nothing else.
export default function EducatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-educator className="grid flex-1 grid-cols-12 gap-x-[var(--space-4)] bg-[var(--surface)] text-[length:var(--text-body)] text-[var(--text)] max-md:pb-[var(--space-7)] md:px-[var(--space-4)] md:pt-[var(--space-4)]">
      <aside className="col-span-2 max-md:hidden">
        <Suspense>
          <EducatorNav as="side" />
        </Suspense>
      </aside>
      <div className="col-span-12 min-w-0 md:col-span-10">{children}</div>
      <div className="md:hidden">
        <Suspense>
          <EducatorNav as="tabs" />
        </Suspense>
      </div>
    </div>
  );
}
