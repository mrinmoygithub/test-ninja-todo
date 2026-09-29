# Todo List

Repository: [github.com/mrinmoygithub/test-ninja-todo](https://github.com/mrinmoygithub/test-ninja-todo)

Single-page todo app (HTML, CSS, JavaScript) served by a small Python Flask app.

**Deploy webhook, SonarQube quality checks, reports, and email notifications** live in the sibling project [`/root/test_ninja_automated_tests`](../test_ninja_automated_tests/README.md) — not in this repo.

Pushes to `master` run the GitHub Actions **Deploy callback** workflow on the self-hosted runner; it POSTs to the local webhook (see automated tests README).

## Run locally (without Docker)

```bash
cd /root/test_ninja
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8080

## Docker

```bash
docker build -t todo-app:latest .
docker run --rm -p 8080:8080 todo-app:latest
```

## GitHub

Add repository secret `DEPLOY_WEBHOOK_SECRET` (same value as on the server). See [test_ninja_automated_tests/deploy/setup-github-secret.sh](../test_ninja_automated_tests/deploy/setup-github-secret.sh).

## Install Docker (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
docker run --rm hello-world
```
