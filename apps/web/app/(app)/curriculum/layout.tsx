import "@/design-system/tokens.css";
import "./screens.css";

export default function CurriculumLayout({ children }: { children: React.ReactNode }) {
  return <div className="cs-page">{children}</div>;
}
