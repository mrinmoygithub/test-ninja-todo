# Todo List + self-hosted CI/CD

Repository: [github.com/mrinmoygithub/test-ninja-todo](https://github.com/mrinmoygithub/test-ninja-todo)

Single-page todo app (HTML, CSS, JavaScript) served by a small Python Flask app. Pushes to `master` run a GitHub Actions workflow on a **self-hosted runner** on this machine; the workflow calls a local deploy webhook that logs the event and rebuilds the Docker image.

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

## Deploy webhook (CI callback)

The webhook listens on `127.0.0.1:9876` and handles `POST /deploy` with header `X-Deploy-Secret`.

### One-time server setup

1. Install Docker (see below if missing).

2. Create env file (use a strong secret):

   ```bash
   sudo mkdir -p /etc/todo-deploy
   sudo cp deploy/deploy-webhook.env.example /etc/todo-deploy/webhook.env
   sudo nano /etc/todo-deploy/webhook.env   # set DEPLOY_WEBHOOK_SECRET
   ```

3. Install and start the systemd unit:

   ```bash
   sudo cp deploy/todo-deploy-webhook.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now todo-deploy-webhook
   sudo systemctl status todo-deploy-webhook
   ```

4. Test manually:

   ```bash
   source /etc/todo-deploy/webhook.env
   curl -fsS -X POST http://127.0.0.1:9876/deploy \
     -H "Content-Type: application/json" \
     -H "X-Deploy-Secret: ${DEPLOY_WEBHOOK_SECRET}" \
     -d '{"ref":"refs/heads/master","sha":"manual-test","repository":"local/test"}'
   tail logs/deploy.log
   ```

Logs:

- `logs/deploy.log` — callback timestamps and build result
- `logs/docker-build.log` — full `docker build` output

### Email notifications

After each deploy callback finishes (success or failure), the webhook sends a plain-text email with deploy log lines and a build output excerpt.

1. Copy the template and set your Gmail app password:

   ```bash
   cp .env.example .env
   nano .env
   ```

   Required variables: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `NOTIFY_EMAIL` (default recipient in the template: sanghrana93@gmail.com).

2. Gmail setup: Google Account → Security → 2-Step Verification → App passwords → create one for Mail.

3. Test SMTP without running a deploy:

   ```bash
   cd /root/test_ninja
   python3 deploy/notify_email.py --test
   ```

4. Test end-to-end (webhook + email):

   ```bash
   source /etc/todo-deploy/webhook.env
   curl -fsS -X POST http://127.0.0.1:9876/deploy \
     -H "Content-Type: application/json" \
     -H "X-Deploy-Secret: ${DEPLOY_WEBHOOK_SECRET}" \
     -d '{"ref":"refs/heads/master","sha":"manual-test","repository":"local/test"}'
   ```

   Check the inbox at `NOTIFY_EMAIL`. After a push to `master`, the **Deploy callback** workflow triggers the same path with the real commit SHA.

If `.env` is missing or incomplete, the webhook still completes; it logs `email notification skipped` to stderr.

## GitHub repository

1. Create an **empty** repo on GitHub (no README), e.g. `test-ninja-todo`.

2. Initialize and push (SSH key must be added to your GitHub account):

   ```bash
   git init -b master
   git add -A
   git commit -m "Initial todo app with self-hosted CI/CD"
   git remote add origin git@github.com:YOUR_USER/test-ninja-todo.git
   git push -u origin master
   ```

3. Add repository secret **Settings → Secrets and variables → Actions**:

   - Name: `DEPLOY_WEBHOOK_SECRET`
   - Value: run `sudo deploy/setup-github-secret.sh` on this server (reads `/etc/todo-deploy/webhook.env`)

4. Ensure this server can push via SSH (`ssh -T git@github.com` should greet your username). If you only added a key on another machine, copy that private key here or generate a new key and add the public key to GitHub.

## Self-hosted GitHub Actions runner

1. GitHub: **Repo → Settings → Actions → Runners → New self-hosted runner** (Linux x64).

2. On this server (outside the repo, e.g. `/opt/actions-runner`):

   ```bash
   mkdir -p /opt/actions-runner && cd /opt/actions-runner
   # Download the tar URL and config commands from GitHub UI, then:
   ./config.sh --url https://github.com/YOUR_USER/test-ninja-todo --token YOUR_TOKEN
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```

3. Confirm the runner shows **Idle** in GitHub.

4. Push to `master`; the **Deploy callback** workflow should succeed and append to `logs/deploy.log`.

## Install Docker (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
docker run --rm hello-world
```
