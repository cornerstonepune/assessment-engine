import { SchoolShell } from "@/components/educator/shell";
import { K2_MENU } from "@/lib/k2-menu";

// The K2 pictures in the school's shell (D-075): white ground, the sidebar (a tab bar on a phone), the school's tokens for
// this shell alone. The engine decides who may look: the educator switch, or the staff preview (`educator.preview_roles`).
export default function K2Layout({ children }: { children: React.ReactNode }) {
  return (
    <SchoolShell items={K2_MENU} label="Children">
      {children}
    </SchoolShell>
  );
}
