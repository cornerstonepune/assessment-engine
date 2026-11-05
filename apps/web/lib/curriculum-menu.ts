import type { MenuItem } from "@/components/educator/shell-nav";

// The curriculum area's menu in the school's shell (D-075): the browser, what is filled and by whom (with the walk-through
// under it), and the skills offered. An activity's page opens from the browser and the fill view.
export const CURRICULUM_MENU: MenuItem[] = [
  { key: "browse", label: "Curriculum", icon: "activity", path: "/curriculum/browse" },
  {
    key: "fill",
    label: "What is filled",
    icon: "checklist",
    path: "/curriculum/fill",
    sub: [
      { key: "all", label: "By part", path: "/curriculum/fill" },
      { key: "walk", label: "Check the drafted parts", path: "/curriculum/fill/walk" },
    ],
  },
  { key: "offers", label: "Skills offered", icon: "skill", path: "/curriculum/offers" },
];
