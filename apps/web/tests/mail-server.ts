import { createServer, type Server } from "node:net";
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";

// A sender of this run's own, so the forgotten-password flow is tested on the email it really sends — no provider, no
// account, no network. It speaks the little of SMTP that nodemailer needs and writes each message it is given to
// MAIL_DIR, which the spec reads (goals/auth-email-password.yaml). It answers the last 250 only after MAIL_WAIT_MS, so
// a page that sent its email before answering the person would take that much longer for a staff email than for an
// email nobody holds — which is exactly what the timing test looks for.
// Beside the run's other leavings, which git ignores: a test email carries a real one-time token and must never
// be committed (rule 6).
export const MAIL_DIR = path.join(__dirname, "..", "test-results", "mail");
export const MAIL_WAIT_MS = 400;

export type Mail = { to: string; body: string };

/** Every message sent to this address, oldest first. */
export function mailFor(to: string): Mail[] {
  let names: string[] = [];
  try {
    names = readdirSync(MAIL_DIR).sort();
  } catch {
    return [];
  }
  return names
    .map((n) => JSON.parse(readFileSync(path.join(MAIL_DIR, n), "utf8")) as Mail)
    .filter((m) => m.to.toLowerCase() === to.toLowerCase());
}

/** The message as a mail reader shows it: a long line sent in quoted-printable comes over split with `=` at the end
 *  of each piece and any `=` of its own written `=3D`, which would cut a link in two. */
function asRead(body: string): string {
  return body.replace(/=\r?\n/g, "").replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

/** The link in a message, as a path on this site: `/login/link?token=…`. */
export function linkIn(mail: Mail): string {
  const found = asRead(mail.body).match(/https?:\/\/[^\s]*\/login\/link\?token=[^\s]+/);
  if (!found) throw new Error("that email carries no set-password link");
  return new URL(found[0]).pathname + new URL(found[0]).search;
}

export function startMailServer(port: number): Server {
  rmSync(MAIL_DIR, { recursive: true, force: true });
  mkdirSync(MAIL_DIR, { recursive: true });
  let n = 0;
  const server = createServer((socket) => {
    let to = "";
    let body: string[] | null = null;
    socket.setEncoding("utf8");
    socket.write("220 mail-server.test\r\n");
    let rest = "";
    socket.on("data", (chunk: string) => {
      rest += chunk;
      const lines = rest.split("\r\n");
      rest = lines.pop() ?? "";
      for (const line of lines) {
        if (body !== null) {
          if (line === ".") {
            writeFileSync(path.join(MAIL_DIR, `${String(++n).padStart(3, "0")}.json`), JSON.stringify({ to, body: body.join("\n") }));
            body = null;
            // slowly, on purpose: a page must have answered before it got here
            setTimeout(() => socket.write("250 taken\r\n"), MAIL_WAIT_MS);
          } else {
            body.push(line.startsWith("..") ? line.slice(1) : line);
          }
          continue;
        }
        const said = line.toUpperCase();
        if (said.startsWith("EHLO") || said.startsWith("HELO")) socket.write("250-mail-server.test\r\n250 AUTH PLAIN LOGIN\r\n");
        else if (said.startsWith("AUTH")) socket.write("235 fine\r\n");
        else if (said.startsWith("MAIL FROM")) socket.write("250 fine\r\n");
        else if (said.startsWith("RCPT TO")) {
          to = line.match(/<([^>]*)>/)?.[1] ?? "";
          socket.write("250 fine\r\n");
        } else if (said === "DATA") {
          body = [];
          socket.write("354 go ahead\r\n");
        } else if (said === "QUIT") {
          socket.write("221 bye\r\n");
          socket.end();
        } else socket.write("250 fine\r\n");
      }
    });
    socket.on("error", () => socket.destroy());
  });
  server.listen(port, "127.0.0.1");
  server.unref();
  return server;
}
