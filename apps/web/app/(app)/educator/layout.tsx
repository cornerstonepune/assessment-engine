import { SchoolShell } from "@/components/educator/shell";
import { EDUCATOR_MENU } from "@/lib/educator/menu";
import { E } from "@/lib/educator/words";

// The K2 educator's screens (M1-09, D-075) in the school's shell, with her menu.
export default function EducatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <SchoolShell items={EDUCATOR_MENU} label={E.nav.label}>
      {children}
    </SchoolShell>
  );
}
