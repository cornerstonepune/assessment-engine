// The site's menu: four groups, and the pages inside each (goals/nav_teacher_scope_and_todo.yaml). Nimish, 24 Oct 2026:
// "They were menus and submenus within the pages. Now this feels like there are like 10 things on the menu." So four
// things sit on the top bar (Teaching went on 26 Oct: goals/nav3_what_needs_doing.yaml); a group's other pages are tabs under it (or in the menu panel), never more items on the bar.
// Pure, so a test can read it. Nothing here names a subject (docs/ux-rules.md rule 11).

export type MenuPage = { href: string; label: string; match: readonly string[] };
export type MenuGroup = { key: string; label: string; href: string; pages: readonly MenuPage[]; setup?: boolean };

export const GROUPS: readonly MenuGroup[] = [
  { key: "doing", label: "What needs doing", href: "/today", pages: [{ href: "/today", label: "What needs doing", match: ["/today"] }] },
  {
    key: "assessments",
    label: "Assessments",
    href: "/papers",
    pages: [
      { href: "/papers", label: "Assessments", match: ["/papers", "/make", "/home", "/worksheets/CS"] },
      { href: "/papers/approve", label: "Papers to approve", match: ["/papers/approve"] },
      { href: "/capture", label: "Upload papers", match: ["/capture"] },
      { href: "/capture/check", label: "Check answers", match: ["/capture/check"] },
    ],
  },
  {
    key: "results",
    label: "Results",
    href: "/growth",
    pages: [
      { href: "/growth", label: "Class results", match: ["/growth"] },
      { href: "/growth/reports", label: "Parent reports", match: ["/growth/reports"] },
      { href: "/across", label: "Across classes", match: ["/across"] },
    ],
  },
  {
    key: "setup",
    label: "Setup",
    href: "/",
    setup: true,
    pages: [
      { href: "/", label: "Curriculum", match: ["/", "/skill-sets", "/worksheets", "/asks"] },
      { href: "/skill-sets/approve", label: "Skills to approve", match: ["/skill-sets/approve"] },
      { href: "/library", label: "Question bank", match: ["/library", "/worksheets/taxonomy"] },
      { href: "/staff", label: "Staff", match: ["/staff"] },
      { href: "/school", label: "School", match: ["/school"] },
    ],
  },
];

const reach = (path: string, m: string) => (m === "/" ? (path === "/" ? 1 : -1) : path.startsWith(m) ? m.length : -1);

/** The page and group a path belongs to: the longest matching prefix, so /papers/approve is its own tab of Assessments. */
export function locate(path: string): { group: MenuGroup; page: MenuPage } | undefined {
  let best: { group: MenuGroup; page: MenuPage; at: number } | undefined;
  for (const group of GROUPS)
    for (const page of group.pages) {
      const at = Math.max(-1, ...page.match.map((m) => reach(path, m)));
      if (at > (best?.at ?? -1)) best = { group, page, at };
    }
  return best;
}

export const groupOf = (path: string) => locate(path)?.group;

/** The tabs under the top bar for a path: the pages of its group, none when the group is one page. */
export function tabsOf(path: string): readonly MenuPage[] {
  const g = groupOf(path);
  return g && g.pages.length > 1 ? g.pages : [];
}
