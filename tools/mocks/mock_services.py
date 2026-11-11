#!/usr/bin/env python3
"""Mock external services for offline development.

Runs three tiny servers so the whole product works without Ollama, a real mail
server, or an internet-facing webhook target:

    Ollama     http://localhost:11434   deterministic AI responses
    SMTP       localhost:1025           accepts mail, prints it, never sends
    Webhook    http://localhost:8099    records deliveries for inspection

Usage::

    python tools/mocks/mock_services.py                # all three
    python tools/mocks/mock_services.py --only ollama
    python tools/mocks/mock_services.py --ollama-port 11435 --webhook-port 8098

Then point the backend at them (see .env.mock or the output banner).

Standard library only — no virtualenv required.
"""

from __future__ import annotations

import argparse
import json
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_TTY = sys.stdout.isatty()
BANNER = "\033[1m" if _TTY else ""
DIM = "\033[2m" if _TTY else ""
RESET = "\033[0m" if _TTY else ""

# ── Ollama ───────────────────────────────────────────────────────────

_MOCK_ANALYSIS = {
    "executive_summary": (
        "This API exposes several high-impact authentication and authorization gaps. "
        "Unauthenticated state-changing endpoints are the most urgent risk because "
        "they can be exercised without any credentials."
    ),
    "priority_actions": [
        "Require authentication on every state-changing endpoint.",
        "Enforce object-level authorization checks on identifier routes.",
        "Add rate limiting to authentication endpoints.",
    ],
    "risk_narrative": (
        "An attacker with no account can create, modify, and delete resources. "
        "Fixing authentication first removes most of the exposure."
    ),
}


class OllamaHandler(BaseHTTPRequestHandler):
    """Minimal stand-in for Ollama's /api/generate and /api/chat."""

    protocol_version = "HTTP/1.1"
    server_version = "MockOllama/1.0"

    def log_message(self, fmt: str, *args) -> None:  # quieter output
        if getattr(self.server, "verbose", False):
            print(f"{DIM}ollama  {fmt % args}{RESET}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path.rstrip("/") == "":
            self._json({"status": "ok", "mock": True})
            return
        self._json({"models": [{"name": "mock-mistral", "size": 0}]})

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            request = {}

        prompt = request.get("prompt") or json.dumps(request.get("messages", []))
        response_text = self._respond(prompt)

        if self.path.rstrip("/").endswith("/api/chat"):
            self._json(
                {
                    "model": request.get("model", "mock-mistral"),
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "message": {"role": "assistant", "content": response_text},
                    "done": True,
                }
            )
            return

        self._json(
            {
                "model": request.get("model", "mock-mistral"),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response": response_text,
                "done": True,
                "eval_count": len(response_text) // 4,
            }
        )

    def _respond(self, prompt: str) -> str:
        lowered = (prompt or "").lower()
        if "json" in lowered or "summary" in lowered:
            return json.dumps(_MOCK_ANALYSIS, indent=2)
        if "remediat" in lowered or "fix" in lowered:
            return (
                "1. Require authentication on every mutating route.\n"
                "2. Validate object ownership before returning data.\n"
                "3. Add per-IP rate limits to login and registration."
            )
        return (
            "Mock analysis: the specification contains several authorization and "
            "authentication weaknesses. Prioritise unauthenticated write endpoints."
        )


# ── Webhook receiver ─────────────────────────────────────────────────


class WebhookHandler(BaseHTTPRequestHandler):
    """Accepts any request, stores it in memory, returns 202."""

    protocol_version = "HTTP/1.1"
    server_version = "MockWebhook/1.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _record(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            decoded = json.loads(body) if body else None
        except json.JSONDecodeError:
            decoded = body.decode("utf-8", "replace")

        entry = {
            "method": method,
            "path": self.path,
            "headers": dict(self.headers),
            "body": decoded,
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        }
        with self.server.lock:  # type: ignore[attr-defined]
            self.server.messages.append(entry)  # type: ignore[attr-defined]

        print(f"{DIM}webhook {method} {self.path} <- {str(decoded)[:120]}{RESET}", flush=True)

        if self.path.startswith("/_requests"):
            payload = json.dumps(self.server.messages[-50:]).encode()  # type: ignore[attr-defined]
        else:
            payload = b'{"status":"received"}'
        self.send_response(202 if not self.path.startswith("/_requests") else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/_requests"):
            payload = json.dumps(self.server.messages[-50:]).encode()  # type: ignore[attr-defined]
        else:
            payload = json.dumps({"status": "ok", "mock": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_POST = lambda self: self._record("POST")  # noqa: E731
    do_PUT = lambda self: self._record("PUT")  # noqa: E731
    do_PATCH = lambda self: self._record("PATCH")  # noqa: E731
    do_DELETE = lambda self: self._record("DELETE")  # noqa: E731


# ── SMTP ─────────────────────────────────────────────────────────────


class SMTPHandler(socketserver.StreamRequestHandler):
    """Just enough SMTP for password-reset mail to succeed locally."""

    def handle(self) -> None:
        self._send("220 mock-smtp ready")
        in_data = False
        message: list[str] = []

        while True:
            line = self.rfile.readline().decode("utf-8", "replace").rstrip("\r\n")
            if not line and not in_data:
                return

            if in_data:
                if line == ".":
                    in_data = False
                    self._store(message)
                    message = []
                    self._send("250 2.0.0 Message accepted")
                else:
                    message.append(line)
                continue

            command = line.upper()
            if command.startswith(("EHLO", "HELO")):
                self._send("250-mock-smtp")
                self._send("250-8BITMIME")
                self._send("250 OK")
            elif command.startswith(("MAIL FROM", "RCPT TO")):
                self._send("250 2.1.0 OK")
            elif command.startswith("DATA"):
                in_data = True
                self._send("354 End data with <CR><LF>.<CR><LF>")
            elif command.startswith("RSET"):
                message = []
                self._send("250 OK")
            elif command.startswith("NOOP"):
                self._send("250 OK")
            elif command.startswith("QUIT"):
                self._send("221 Bye")
                return
            else:
                self._send("250 OK")

    def _store(self, message: list[str]) -> None:
        text = "\n".join(message)
        with self.server.lock:  # type: ignore[attr-defined]
            self.server.messages.append(text)  # type: ignore[attr-defined]
        first = next((line for line in message if line.strip()), "")
        print(f"{DIM}smtp    received {len(message)} lines | {first[:80]}{RESET}", flush=True)
        for line in message:
            if line.lower().startswith(("subject:", "to:")):
                print(f"{DIM}smtp    {line}{RESET}", flush=True)

    def _send(self, line: str) -> None:
        self.wfile.write((line + "\r\n").encode())


class SMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.messages: list[str] = []
        self.lock = threading.Lock()


# ── Runner ───────────────────────────────────────────────────────────


def serve(server, name: str, url: str) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, name=name, daemon=True)
    thread.start()
    print(f"  {BANNER}{name:<8}{RESET} {url}", flush=True)
    return thread


def main() -> int:
    parser = argparse.ArgumentParser(description="Mock Ollama, SMTP, and webhook services.")
    parser.add_argument("--only", help="Comma-separated subset: ollama,smtp,webhook")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ollama-port", type=int, default=11434)
    parser.add_argument("--smtp-port", type=int, default=1025)
    parser.add_argument("--webhook-port", type=int, default=8099)
    parser.add_argument("--verbose", action="store_true", help="Log every request.")
    args = parser.parse_args()

    wanted = {"ollama", "smtp", "webhook"}
    if args.only:
        wanted = {part.strip().lower() for part in args.only.split(",") if part.strip()}

    print("\nMock services starting...\n", flush=True)
    started = 0

    if "ollama" in wanted:
        ollama = ThreadingHTTPServer((args.host, args.ollama_port), OllamaHandler)
        ollama.verbose = args.verbose  # type: ignore[attr-defined]
        serve(ollama, "ollama", f"http://{args.host}:{args.ollama_port}/api/generate")
        started += 1

    if "webhook" in wanted:
        webhook = ThreadingHTTPServer((args.host, args.webhook_port), WebhookHandler)
        webhook.messages = []  # type: ignore[attr-defined]
        webhook.lock = threading.Lock()  # type: ignore[attr-defined]
        serve(
            webhook,
            "webhook",
            f"http://{args.host}:{args.webhook_port}/  (inspect: /_requests)",
        )
        started += 1

    if "smtp" in wanted:
        smtp = SMTPServer((args.host, args.smtp_port), SMTPHandler)
        serve(smtp, "smtp", f"smtp://{args.host}:{args.smtp_port}")
        started += 1

    if started == 0:
        print("Nothing started — check --only.", flush=True)
        return 1

    print(
        f"\n  {DIM}Point the backend at them:{RESET}\n"
        f"    OLLAMA_URL=http://{args.host}:{args.ollama_port}/api/generate\n"
        f"    SMTP_HOST={args.host}  SMTP_PORT={args.smtp_port}  SMTP_USE_TLS=false\n"
        f"    WEBHOOK_URL=http://{args.host}:{args.webhook_port}/events\n"
        f"\n  {DIM}Ctrl-C to stop{RESET}\n",
        flush=True,
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping mocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
