#!/usr/bin/env python3
"""Send deploy CI/CD completion emails via Gmail SMTP."""

from __future__ import annotations

import argparse
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
BUILD_EXCERPT_MAX = 4000
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_dotenv(path: Path) -> dict[str, str]:
    """Load simple KEY=value lines from a .env file (no export prefix, # comments)."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def _mail_config() -> tuple[str, str, str] | None:
    env = load_dotenv(ENV_PATH)
    user = env.get("GMAIL_USER", "").strip()
    password = env.get("GMAIL_APP_PASSWORD", "").strip()
    notify = env.get("NOTIFY_EMAIL", "").strip()
    if not user or not password or not notify:
        return None
    return user, password, notify


def _truncate_excerpt(text: str, limit: int = BUILD_EXCERPT_MAX) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text or "(no build output captured)"
    return "...(truncated)...\n" + text[-limit:]


def _build_body(
    *,
    success: bool,
    repository: str,
    ref: str,
    sha: str,
    deploy_lines: list[str],
    build_excerpt: str,
) -> str:
    status = "succeeded" if success else "failed"
    lines = [
        f"CI/CD deploy {status}",
        "",
        f"Time (UTC): {utc_now()}",
        f"Repository: {repository or '(unknown)'}",
        f"Ref: {ref or '(unknown)'}",
        f"SHA: {sha or '(unknown)'}",
        "",
        "Deploy log (this run):",
        *deploy_lines,
        "",
        "Build log excerpt:",
        _truncate_excerpt(build_excerpt),
    ]
    return "\n".join(lines)


def send_deploy_notification(
    *,
    success: bool,
    repository: str,
    ref: str,
    sha: str,
    deploy_lines: list[str],
    build_excerpt: str,
) -> None:
    cfg = _mail_config()
    if cfg is None:
        print(
            "email notification skipped: set GMAIL_USER, GMAIL_APP_PASSWORD, and NOTIFY_EMAIL in .env",
            file=sys.stderr,
        )
        return

    gmail_user, app_password, notify_email = cfg
    label = "succeeded" if success else "failed"
    repo_label = repository or "unknown"
    subject = f"[CI/CD] Deploy {label} — {repo_label}"
    body = _build_body(
        success=success,
        repository=repository,
        ref=ref,
        sha=sha,
        deploy_lines=deploy_lines or ["(no deploy log lines)"],
        build_excerpt=build_excerpt,
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = notify_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(gmail_user, app_password)
        smtp.send_message(msg)

    print(f"deploy notification email sent to {notify_email}", file=sys.stderr)


def send_test_email() -> None:
    cfg = _mail_config()
    if cfg is None:
        print(
            "Cannot send test email: set GMAIL_USER, GMAIL_APP_PASSWORD, and NOTIFY_EMAIL in .env",
            file=sys.stderr,
        )
        sys.exit(1)

    send_deploy_notification(
        success=True,
        repository="test/manual",
        ref="refs/heads/master",
        sha="notify-email-test",
        deploy_lines=[
            f"{utc_now()} | trigger received | repo=test/manual ref=refs/heads/master sha=notify-email-test",
            f"{utc_now()} | docker build ok | image=todo-app:latest",
        ],
        build_excerpt="Test notification from deploy/notify_email.py --test\n(no docker build was run)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy CI/CD email notifications")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test email using credentials from .env",
    )
    args = parser.parse_args()
    if args.test:
        send_test_email()
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
