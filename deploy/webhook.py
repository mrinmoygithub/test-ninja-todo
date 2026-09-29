#!/usr/bin/env python3
"""Local deploy webhook: log CI callbacks and rebuild the Docker image."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_DEPLOY_DIR = Path(__file__).resolve().parent
if str(_DEPLOY_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPLOY_DIR))
from notify_email import send_deploy_notification

REPO_ROOT = _DEPLOY_DIR.parent
LOG_DIR = REPO_ROOT / "logs"
DEPLOY_LOG = LOG_DIR / "deploy.log"
BUILD_LOG = LOG_DIR / "docker-build.log"
IMAGE_TAG = "todo-app:latest"
HOST = os.environ.get("DEPLOY_WEBHOOK_HOST", "127.0.0.1")
PORT = int(os.environ.get("DEPLOY_WEBHOOK_PORT", "9876"))
SECRET = os.environ.get("DEPLOY_WEBHOOK_SECRET", "")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_line(path: Path, line: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_docker_build() -> tuple[int, str]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    append_line(BUILD_LOG, f"--- build started {utc_now()} ---")
    proc = subprocess.run(
        ["docker", "build", "-t", IMAGE_TAG, "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    with BUILD_LOG.open("a", encoding="utf-8") as f:
        if proc.stdout:
            f.write(proc.stdout)
        if proc.stderr:
            f.write(proc.stderr)
    append_line(BUILD_LOG, f"--- build finished exit={proc.returncode} {utc_now()} ---")
    combined = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, combined


class DeployHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _send_json(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if self.path != "/deploy":
            self._send_json(404, {"ok": False, "error": "not found"})
            return

        if not SECRET:
            self._send_json(500, {"ok": False, "error": "webhook secret not configured"})
            return

        provided = self.headers.get("X-Deploy-Secret", "")
        if provided != SECRET:
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "invalid json"})
            return

        ref = payload.get("ref", "")
        sha = payload.get("sha", "")
        repository = payload.get("repository", "")

        deploy_lines: list[str] = []
        trigger_line = f"{utc_now()} | trigger received | repo={repository} ref={ref} sha={sha}"
        deploy_lines.append(trigger_line)
        append_line(DEPLOY_LOG, trigger_line)

        code, detail = run_docker_build()
        build_excerpt = detail
        if code != 0:
            result_line = f"{utc_now()} | docker build failed | exit={code}"
            deploy_lines.append(result_line)
            append_line(DEPLOY_LOG, result_line)
            try:
                send_deploy_notification(
                    success=False,
                    repository=repository,
                    ref=ref,
                    sha=sha,
                    deploy_lines=deploy_lines,
                    build_excerpt=build_excerpt,
                )
            except Exception as exc:
                print(f"email notification failed: {exc}", file=sys.stderr)
            self._send_json(500, {"ok": False, "error": "docker build failed", "detail": detail[-2000:]})
            return

        result_line = f"{utc_now()} | docker build ok | image={IMAGE_TAG}"
        deploy_lines.append(result_line)
        append_line(DEPLOY_LOG, result_line)
        try:
            send_deploy_notification(
                success=True,
                repository=repository,
                ref=ref,
                sha=sha,
                deploy_lines=deploy_lines,
                build_excerpt=build_excerpt,
            )
        except Exception as exc:
            print(f"email notification failed: {exc}", file=sys.stderr)
        self._send_json(200, {"ok": True, "built": IMAGE_TAG})


def main() -> None:
    if not SECRET:
        print("DEPLOY_WEBHOOK_SECRET is required", file=sys.stderr)
        sys.exit(1)
    server = HTTPServer((HOST, PORT), DeployHandler)
    print(f"Deploy webhook listening on http://{HOST}:{PORT}/deploy", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
