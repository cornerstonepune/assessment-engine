import { locate } from "./menu";

// Where the Guide explains a page of the site (goals/guide_for_educators.yaml): pure, so the header's "?" can use it
// in the browser without the guide's words. A menu page's guide is its label in small words joined by dashes
// ("Papers to approve" → /guide/papers-to-approve); packages/engine/tests/test_guide.py names its files the same way.

export const slugOf = (label: string) => label.toLowerCase().replace(/[^a-z]+/g, "-").replace(/^-|-$/g, "");

/** The guide page for a path of the site: its menu page's, or none (the guide's own pages, a page on no menu item). */
export function guideFor(path: string): string | undefined {
  const page = locate(path)?.page;
  return page && !path.startsWith("/guide") ? `/guide/${slugOf(page.label)}` : undefined;
}
