/**
 * M1-09 — the K2 educator's screens are held to the brand's tokens and the chip says one thing everywhere
 * (goals/m1-09-educator-screens.yaml, D-073). No browser, no database: the tokens file and the chip rule, read directly.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { TEXT_PAIRS, contrast, readTokens } from "./tokens-file";
import { chipOf, nowAt } from "../lib/educator/chip";
import { isDay } from "../lib/educator/period";

const T = readTokens(); // apps/web/design-system/tokens.css, the school's one tokens file (D-073)
const px = (v: string) => (v.endsWith("rem") ? parseFloat(v) * 16 : parseFloat(v));

test("spacing is on the 8 px scale, taps are at least 44 px, one type scale, one font system", () => {
  const space = Object.keys(T).filter((k) => /^--space-\d+$/.test(k));
  expect(space.length).toBeGreaterThan(4);
  for (const k of space) expect(k === "--space-1" ? px(T[k]) === 4 : px(T[k]) % 8 === 0, `${k} ${T[k]}`).toBe(true); // 4 inside a control only
  expect(px(T["--tap"])).toBeGreaterThanOrEqual(44);
  const scale = ["--text-caption", "--text-label", "--text-body", "--text-lead", "--text-h3", "--text-h2", "--text-h1"].map((k) => px(T[k]));
  expect(scale).toEqual([12, 14, 16, 18, 20, 24, 32]);
  expect(T["--font-body"]).toMatch(/^"Jost", sans-serif$/);
  expect(T["--font-display"]).toMatch(/^"Cormorant Garamond", serif$/);
  expect(T["--font-script"]).toMatch(/^"Eczar", serif$/);
});

test("every text colour on its background reaches 4.5:1", () => {
  for (const [fg, bg] of TEXT_PAIRS) expect(contrast(T[fg], T[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
});

test("every token the educator's screens name is in tokens.css", () => {
  const own = new Set(["--c", "--r", "--b", "--d", "--font-jost", "--font-cormorant", "--font-eczar", "--font-heading"]); // a chip's three, the fonts
  const files = [...sources()];
  for (const f of files)
    for (const [, name] of readFileSync(f, "utf8").matchAll(/var\((--[\w-]+)/g))
      if (!own.has(name)) expect(T[name], `${path.basename(f)}: ${name}`).toBeDefined();
});

function* sources(): Generator<string> {
  const walk = function* (d: string): Generator<string> {
    for (const f of readdirSync(d)) {
      const p = path.join(d, f);
      if (statSync(p).isDirectory()) yield* walk(p);
      else if (/\.tsx?$/.test(p)) yield p;
    }
  };
  for (const d of ["../app/(app)/educator", "../components/educator"]) yield* walk(path.resolve(__dirname, d));
}

test("the educator's screens write no colour, size or font of their own: only the tokens", () => {
  const files = [...sources()];
  expect(files.length).toBeGreaterThan(0);
  for (const f of files) {
    const src = readFileSync(f, "utf8");
    expect(src, `${f}: a colour literal`).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
    expect(src, `${f}: a pixel size of its own`).not.toMatch(/\b\d+px\b/);
    expect(src, `${f}: a Tailwind colour or text size`).not.toMatch(/\b(?:text|bg|border)-(?:\[(?!(?:length:|color:)?var)|(?:red|green|blue|gray|slate|basalt|neem|bamboo|terracotta|monsoon|mud|chalk|lime)\b)/);
    expect(src, `${f}: an emoji`).not.toMatch(/\p{Extended_Pictographic}/u);
  }
});

test("a chip is one thing everywhere: Do now in the period, none on a period still to come, Done and Late only from a record, none for a fixed or empty period", () => {
  const p = { starts_at: "11:20", ends_at: "11:40", kind: "subject" as const, state: "planned" as const };
  const at = (now: string, day: "past" | "today" | "future" = "today") => chipOf(p, { now, day });
  expect(at("11:35")).toBe("doNow");
  expect(at("11:00")).toBe(null); // D-075: a future cell has no chip; the countdown says when
  expect(at("09:00", "future")).toBe(null);
  expect(at("12:00")).toBe(null); // over, nothing recorded yet: no chip, never a guess
  expect(chipOf({ ...p, state: "done" }, { now: "12:00", day: "today" })).toBe("done");
  expect(chipOf({ ...p, state: "not_done" }, { now: "12:00", day: "today" })).toBe("late");
  expect(chipOf({ ...p, kind: "fixed" }, { now: "11:35", day: "today" })).toBe(null);
  expect(chipOf({ ...p, kind: "empty" }, { now: "11:35", day: "today" })).toBe(null);
  expect(chipOf({ ...p, ends_at: null }, { now: "11:35", day: "today" })).toBe("doNow"); // the day's last: to its end
});

test("the Now line falls before the first period still to come, after the one running, and nowhere before or after the day", () => {
  const ps = [
    { starts_at: "08:30", ends_at: "08:45" },
    { starts_at: "09:40", ends_at: "10:00" },
    { starts_at: "10:00", ends_at: "10:20" },
  ];
  expect(nowAt(ps, "09:50")).toBe(2); // running 09:40: the line sits under it
  expect(nowAt(ps, "09:00")).toBe(1);
  expect(nowAt(ps, "08:00")).toBe(null); // before the day
  expect(nowAt(ps, "11:00")).toBe(null); // after it
  expect(nowAt([...ps, { starts_at: "13:25", ends_at: null }], "13:40")).toBe(4); // the last has no end: still running
});

test("a day in the address is a real date or nothing", () => {
  expect(isDay("2026-11-23")).toBe(true);
  expect(isDay("foo")).toBe(false);
  expect(isDay("2026-13-40")).toBe(false);
  expect(isDay(undefined)).toBe(false);
});
