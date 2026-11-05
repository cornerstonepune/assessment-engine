import "./screens.css";
import { SchoolShell } from "@/components/educator/shell";
import { CURRICULUM_MENU } from "@/lib/curriculum-menu";

// The curriculum screens in the school's shell (D-075): the area's menu down the left, a tab bar at the foot of a phone.
export default function CurriculumLayout({ children }: { children: React.ReactNode }) {
  return (
    <SchoolShell items={CURRICULUM_MENU} label="Curriculum">
      <div className="cs-page">{children}</div>
    </SchoolShell>
  );
}
