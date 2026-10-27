import { createServer, type Server } from "node:http";
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

// A GitHub of this run's own, so a note from staff is tested on the issue it really makes — never the real GitHub
// (goals/feed_report_from_the_tool.yaml). It answers the two calls lib/github.ts makes: make an issue, and list the
// issues labelled `from-the-tool`. Each issue made is a file in GITHUB_DIR, which the spec reads and may edit (close
// it, add a label) to stand for what Nimish does on GitHub. A file `down` in the folder makes it answer 503.
export const GITHUB_DIR = path.join(__dirname, "..", "test-results", "github");
export const TEST_TOKEN = "test-token-of-this-run-and-no-one-s";

export type Issue = { number: number; title: string; body: string; labels: string[]; state: "open" | "closed"; auth: string };

export function issuesMade(): Issue[] {
  let names: string[] = [];
  try {
    names = readdirSync(GITHUB_DIR).filter((n) => n.endsWith(".json")).sort();
  } catch {
    return [];
  }
  return names.map((n) => JSON.parse(readFileSync(path.join(GITHUB_DIR, n), "utf8")) as Issue);
}

export function changeIssue(number: number, change: Partial<Issue>): void {
  const file = path.join(GITHUB_DIR, `${String(number).padStart(4, "0")}.json`);
  writeFileSync(file, JSON.stringify({ ...JSON.parse(readFileSync(file, "utf8")), ...change }));
}

/** GitHub answering 503 until `githubUp()`. */
export function githubDown(): void {
  writeFileSync(path.join(GITHUB_DIR, "down"), "");
}
export function githubUp(): void {
  rmSync(path.join(GITHUB_DIR, "down"), { force: true });
}

export function startGithubServer(port: number): Server {
  rmSync(GITHUB_DIR, { recursive: true, force: true });
  mkdirSync(GITHUB_DIR, { recursive: true });
  const server = createServer((req, res) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      const send = (status: number, body: unknown) => {
        res.writeHead(status, { "Content-Type": "application/json" });
        res.end(JSON.stringify(body));
      };
      if (readdirSync(GITHUB_DIR).includes("down")) return send(503, { message: "down" });
      if (req.headers.authorization !== `Bearer ${TEST_TOKEN}`) return send(401, { message: "Bad credentials" });
      const url = new URL(req.url ?? "/", "http://github.test");
      if (url.pathname !== "/repos/cornerstonepune/assessment-engine/issues") return send(404, { message: "Not Found" });
      if (req.method === "POST") {
        const { title, body, labels } = JSON.parse(raw) as Issue;
        const number = issuesMade().length + 1;
        const issue: Issue = { number, title, body, labels, state: "open", auth: "token" };
        writeFileSync(path.join(GITHUB_DIR, `${String(number).padStart(4, "0")}.json`), JSON.stringify(issue));
        return send(201, { number });
      }
      const label = url.searchParams.get("labels");
      return send(
        200,
        issuesMade()
          .filter((i) => !label || i.labels.includes(label))
          .reverse()
          .map((i) => ({ number: i.number, state: i.state, labels: i.labels.map((name) => ({ name })) })),
      );
    });
  });
  server.listen(port, "127.0.0.1");
  return server;
}
