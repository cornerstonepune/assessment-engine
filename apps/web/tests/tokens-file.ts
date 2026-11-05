import { readFileSync } from "node:fs";
import path from "node:path";

// The tokens test's reader of apps/web/design-system/tokens.css (D-073), the one file the K2 educator's screens take
// every value from: a component writes a token's name, never a value. TEXT_PAIRS is each text colour those screens draw
// on its background, held to 4.5:1.
export const TEXT_PAIRS = [
  ["--text", "--bg"],
  ["--text-muted", "--bg"],
  ["--text", "--surface"],
  ["--text-muted", "--surface"],
  ["--link", "--bg"],
  ["--chip-donow-fg", "--chip-donow-bg"],
  ["--chip-confirm-fg", "--chip-confirm-bg"],
  ["--chip-soon-fg", "--chip-soon-bg"],
  ["--chip-done-fg", "--chip-done-bg"],
  ["--chip-late-fg", "--chip-late-bg"],
  ["--origin-school-fg", "--origin-school-bg"],
  ["--origin-drafted-fg", "--origin-drafted-bg"],
  ["--origin-edited-fg", "--origin-edited-bg"],
] as const;

/** The light-mode `:root` of tokens.css as name → value, var() chains resolved (for the test; never at run time). */
export function readTokens(file = path.resolve(__dirname, "../design-system/tokens.css")): Record<string, string> {
  const css = readFileSync(file, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const root = css.slice(css.indexOf(":root"), css.indexOf("@media"));
  const raw = Object.fromEntries([...root.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
  const resolve = (v: string, depth = 0): string => {
    const m = /^var\((--[\w-]+)\)$/.exec(v);
    return m && depth < 10 && raw[m[1]] ? resolve(raw[m[1]], depth + 1) : v;
  };
  return Object.fromEntries(Object.keys(raw).map((k) => [k, resolve(raw[k])]));
}

/** WCAG contrast of two #rrggbb colours. */
export function contrast(a: string, b: string): number {
  const lum = (h: string) => {
    const [r, g, bl] = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}
