"""`bin/ci-postgres` retries its downloads (goals/ci-postgres-retry.yaml).

It failed about 90 seconds in with `curl: (56) Failure when receiving data from the peer` on five CI runs of 2026-11-04,
before any test, each cured by a re-run. The script downloads three times (the signing key with curl, `apt-get update`,
`apt-get install`) and none was tried again. These tests read the script's own retry settings and run them: curl, with
the script's flags, against a local server that drops the connection part-way; and the script's `retry` function.
"""

import re
import socketserver
import subprocess
import threading
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "bin" / "ci-postgres"
BODY = b"-----BEGIN PGP PUBLIC KEY BLOCK-----\n" + b"x" * 400 + b"\n-----END PGP PUBLIC KEY BLOCK-----\n"


def _curl_flags() -> list[str]:
    """The script's own `CURL_RETRY=( … )` words, with the delay made one second so a test does not sit through it (0 would mean curl's own backoff, which grows)."""
    found = re.search(r"^CURL_RETRY=\((.*?)\)\s*$", SCRIPT.read_text(), re.MULTILINE)
    assert found, "bin/ci-postgres defines no CURL_RETRY=( … ) for its key fetch"
    flags = found.group(1).split()
    assert "--retry-all-errors" in flags, "a transfer error (curl 56) is retried only with --retry-all-errors"
    delay = flags[flags.index("--retry-delay") + 1] if "--retry-delay" in flags else "0"
    assert int(delay) >= 1, "a retry with no delay hammers a server that has just dropped us"
    return [("1" if f == delay else f) for f in flags]


class _Drops(socketserver.StreamRequestHandler):
    """Promises the key, sends part of it, and hangs up: what curl reports as a failure receiving data."""

    def handle(self):
        self.server.requests += 1
        while self.rfile.readline() not in (b"\r\n", b"\n", b""):
            pass
        if self.server.requests <= self.server.drops:
            self.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(BODY) + BODY[:50])
            return
        self.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(BODY) + BODY)


def _fetch(tmp_path, drops: int):
    """curl with the script's flags and its `-fsS`, against a server that drops its first `drops` answers.
    → (curl's exit code, the file it wrote, how many times the server was asked)."""
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Drops)
    server.requests, server.drops, server.daemon_threads = 0, drops, True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    out = tmp_path / "key.asc"
    try:
        done = subprocess.run(
            [
                "curl",
                "-fsS",
                "-o",
                str(out),
                *_curl_flags(),
                f"http://127.0.0.1:{server.server_address[1]}/key.asc",
            ],
            capture_output=True,
            timeout=60,
        )
    finally:
        server.shutdown()
    return done.returncode, out.read_bytes() if out.exists() else b"", server.requests


def test_a_key_fetch_that_drops_part_way_is_tried_again_and_succeeds(tmp_path):
    code, got, asked = _fetch(tmp_path, drops=2)
    assert (code, got, asked) == (0, BODY, 3), (
        f"curl exit {code}, {len(got)} bytes, server asked {asked} times"
    )


def test_a_fetch_that_always_fails_fails_the_step_after_its_last_attempt(tmp_path):
    code, got, asked = _fetch(tmp_path, drops=10**6)
    assert code != 0, "a key that never arrives must fail the step, not pass with half a key"
    assert asked > 2, f"curl gave up after {asked} attempt(s)"
    # the script's `retry` function for the apt commands: loud, naming the command, after its last attempt
    code, said = _retry("false")
    assert code != 0
    assert "giving up" in said and "false" in said, said
    code, said = _retry('n=$(cat "$COUNT"); echo $((n + 1)) > "$COUNT"; [ "$n" -ge 2 ]', count=True)
    assert code == 0, f"a command that fails twice and then works should pass: {said}"


def _retry(command: str, count: bool = False):
    """Run the script's own `retry` function on `command`, with `sleep` made instant. → (exit code, what it said)."""
    text = SCRIPT.read_text()
    found = re.search(r"^retry\(\) \{.*?^\}", text, re.MULTILINE | re.DOTALL)
    assert found, "bin/ci-postgres defines no retry() function"
    setup = 'COUNT=$(mktemp); echo 0 > "$COUNT"; export COUNT; ' if count else ""
    done = subprocess.run(
        ["bash", "-c", f"sleep() {{ :; }}\n{found.group(0)}\n{setup}retry bash -c '{command}'"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return done.returncode, done.stderr


def test_every_download_in_the_script_goes_through_a_retry():
    lines = [ln.strip() for ln in SCRIPT.read_text().splitlines() if not ln.strip().startswith("#")]
    curls = [ln for ln in lines if re.search(r"\bcurl\b", ln) and "CURL_RETRY=" not in ln]
    apts = [ln for ln in lines if re.search(r"\bapt-get\b.*\b(update|install)\b", ln)]
    assert curls and apts
    assert all('"${CURL_RETRY[@]}"' in ln for ln in curls), f"a curl without the retry flags: {curls}"
    assert all(ln.startswith("retry ") and "Acquire::Retries" in ln for ln in apts), (
        f"an apt-get without `retry` and its own Acquire::Retries: {apts}"
    )
