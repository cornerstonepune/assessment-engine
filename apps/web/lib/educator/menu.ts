import type { MenuItem } from "@/components/educator/shell-nav";
import { E } from "./words";

// The K2 educator's menu (D-075's order): Today, then the timetable (a day, this week, next week). Fortnight, month,
// materials (the class's list, the school's, the notes to read); activities and children come with their screens.
export const EDUCATOR_MENU: MenuItem[] = [
  { key: "today", label: E.today.title, icon: "today", path: "/educator", also: ["/educator/period", "/educator/activity"] },
  {
    key: "week",
    label: E.nav.timetable,
    icon: "week",
    path: "/educator/week",
    sub: [
      { key: "day", label: E.nav.day, path: "/educator", extra: "tomorrow" },
      { key: "week", label: E.week.title, path: "/educator/week" },
      { key: "next", label: E.weekNav.next, path: "/educator/week", extra: "next" },
    ],
  },
  {
    key: "materials",
    label: E.materials.nav,
    icon: "checklist",
    path: "/educator/materials",
    also: ["/educator/materials/"],
    sub: [
      { key: "class-list", label: E.materials.classList, path: "/educator/materials" },
      { key: "school-list", label: E.materials.schoolList, path: "/educator/materials/school" },
      { key: "review", label: E.materials.review, path: "/educator/materials/review" },
    ],
  },
];
