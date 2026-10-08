# Operate the Career Platform VM Implementation Plan

## VM details

- VM: `vm-career-platform`
- Resource group: `RG-CAREER-PLATFORM`
- Public IP: `9.205.27.2`
- Status: running
- Location: `denmarkeast`
- SSH user: `azureuser`
- App directory: `/home/azureuser/career-platform`
- App port: `8000` (loopback only); public website: HTTP port `80`

**Goal:** Serve the existing FastAPI site at `http://9.205.27.2`, start it on boot, and recover from worker or service failures.

**Architecture:** Nginx listens on public-facing port 80 and forwards requests to Uvicorn on `127.0.0.1:8000`. A systemd service runs two Uvicorn workers as `azureuser`; systemd starts the service at boot and restarts it after a failure. The existing checkout, virtual environment, and SQLite database stay in place.

**Tech Stack:** Ubuntu, systemd, Nginx, Uvicorn, FastAPI, SQLite, Azure Network Security Group (NSG).

**Spec:** User request in this conversation; related deployment history: `docs/superpowers/plans/2026-09-24-azure-vm-migration.md`.

## Constraints

- Do not use Azure CLI or change Azure resources.
- The owner adds the Azure NSG rule in the portal: `Allow-HTTP-80`, TCP port `80`, priority `320`.
- Keep public port `8000` closed; Uvicorn must bind only to `127.0.0.1`.
- Run the application process as `azureuser`, never root.
- Use `/home/azureuser/career-platform`, its existing `.venv`, and `/var/lib/career-platform/career-platform.db`.
- Do not edit repository application files or add tests. Do not perform crash/restart tests.
- Keep the work small: roughly 20 minutes of commands and checks.

## Plan

### 1. Confirm the existing VM setup

**Where:** Azure portal (read-only), then VM in an SSH session as `azureuser`.

**What and why:** In the Azure portal, inspect the VM's Public IP resource and confirm its IP assignment is **Static**. This is a read-only check; do not change the allocation or address. Then confirm the shell user, checkout, virtual environment, environment file, database, and current process state before installing anything. This avoids replacing the existing app or data. VM commands: `whoami`; `test -x /home/azureuser/career-platform/.venv/bin/uvicorn`; `test -f /home/azureuser/career-platform/.env`; `test -f /var/lib/career-platform/career-platform.db`; `pgrep -af 'uvicorn|nginx' || true`.

**Verify:** The portal shows the public IP assignment as `Static`; no allocation setting was changed. The VM user is `azureuser` and all three paths exist. Note any existing Uvicorn/Nginx processes so they can be stopped or reused deliberately.

**Undo:** Read-only checks make no changes; exit SSH if desired.

### 2. Install and configure the app service

**Where:** VM, SSH shell. Use `sudo` only to install packages and write system configuration; the service itself runs unprivileged.

**What and why:** Install Nginx if it is missing (`sudo apt-get update && sudo apt-get install -y nginx`). Create `/etc/systemd/system/career-platform.service` with `User=azureuser`, `Group=azureuser`, `WorkingDirectory=/home/azureuser/career-platform`, `EnvironmentFile=/home/azureuser/career-platform/.env`, and `ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2`. Set `Restart=on-failure` and `RestartSec=3`; order it after the network and enable it under `multi-user.target`. Two workers let the surviving worker continue serving while Uvicorn replaces a failed worker; systemd brings the service back if the whole service exits.

Reload systemd and enable/start it: `sudo systemctl daemon-reload && sudo systemctl enable --now career-platform`.

**Verify:** `systemctl is-enabled career-platform` prints `enabled`; `systemctl is-active career-platform` prints `active`; `systemctl show career-platform -p User -p MainPID` identifies the service user as `azureuser`. `curl -fsS http://127.0.0.1:8000/` returns the homepage. `sudo ss -ltnp` shows port 8000 bound only to `127.0.0.1`.

**Undo:** Stop and disable the service with `sudo systemctl disable --now career-platform`, then remove only `/etc/systemd/system/career-platform.service` and run `sudo systemctl daemon-reload`. This leaves the checkout and database intact.

### 3. Configure Nginx as the public front door

**Where:** VM, SSH shell.

**What and why:** Create `/etc/nginx/sites-available/career-platform` with a server listening on port 80 and `server_name 9.205.27.2`, proxying `/` to `http://127.0.0.1:8000`. Forward the original `Host`, client address (`X-Real-IP`, `X-Forwarded-For`), and scheme (`X-Forwarded-Proto`). Enable it with a symlink in `sites-enabled`, remove the default site symlink if it conflicts, then run `sudo nginx -t && sudo systemctl enable --now nginx && sudo systemctl reload nginx`. Nginx accepts visitor traffic; only the app runs as `azureuser`.

**Verify:** `sudo nginx -t` reports a successful configuration; `systemctl is-enabled nginx` prints `enabled`; `curl -fsS http://127.0.0.1/` returns the homepage. From the laptop, after the portal rule is added, `curl -I http://9.205.27.2/` returns an HTTP response. In the Azure portal, confirm `Allow-HTTP-80` is TCP/80 at priority 320 and no inbound allow rule exposes TCP/8000.

**Undo:** Remove the `career-platform` Nginx symlink and site file, restore the default site if it was removed, run `sudo nginx -t`, and reload Nginx. Remove only the NSG rule you added if you want to close public HTTP again.

### 4. Finish with read-only operating checks

**Where:** VM over SSH, then laptop and Azure portal.

**What and why:** Check `systemctl status career-platform nginx --no-pager`, `journalctl -u career-platform -n 30 --no-pager`, local HTTP on ports 80 and 8000, and the listener address. These checks confirm the service and reverse proxy are healthy without intentionally causing a failure.

**Verify:** Both services are active; the local homepage responds through Nginx; Uvicorn listens only on loopback; the laptop can load `http://9.205.27.2`; the Azure portal has the requested port 80 rule and no public port 8000 rule. Do not perform crash/restart tests in this work.

**Undo:** These checks are read-only. Use the rollback steps above if configuration needs to be removed.

### 5. Record the final network and service state

**Where:** VM over SSH, Azure portal, and this plan's execution notes.

**What and why:** Record every listening port shown by `sudo ss -ltnp`, including the local address and program for each listener. Record the VM's private IP and public IP. In the Azure portal, record each inbound NSG rule's name, priority, protocol, port, source, action, and purpose so an owner can tell why it exists. Include the `Allow-HTTP-80` rule and explain that it permits public website traffic; explain any SSH rule as administrative access. Do not change IP allocation or NSG rules while collecting this information.

**Verify:** The record accounts for every listening port and every inbound NSG rule, and lists both VM IP addresses. Before committing or pushing the plan, remove sensitive values such as the laptop's public IP and Azure subscription ID.

**Undo:** Recording is read-only. If notes contain sensitive values, redact them before saving or sharing; no VM or Azure rollback is needed.

---

**Review note:** The repository already has uncommitted changes in `README.md` and an untracked `PRD-v1.0.md`. Leave those as they are. This plan is the only intended file change.

## Execution record — 2026-10-08

- **Services:** `career-platform` and `nginx` are enabled and active. The app service runs as `azureuser` with two Uvicorn workers. Recent journal entries show successful application startup and HTTP 200 responses.
- **HTTP checks:** GET requests to `127.0.0.1:80`, `127.0.0.1:8000`, and `http://9.205.27.2/` returned the homepage. The laptop's `curl -I` request returned HTTP 405 because the app does not allow the HEAD method; the GET check succeeded.
- **VM IPs:** Private IP `172.16.0.4`; public IP `9.205.27.2` (allocation confirmed Static in Azure portal by the owner).
- **Listening sockets:** `0.0.0.0:22` and `[::]:22` — `sshd` (with systemd socket descriptors); `0.0.0.0:80` — Nginx; `127.0.0.1:8000` — Uvicorn/Python workers; `127.0.0.54:53` and `127.0.0.53%lo:53` — `systemd-resolve`.
- **Inbound NSG rules (owner-verified):** SSH — inbound Allow, TCP/22, source restricted to the owner's laptop `/32` (address omitted), for VM administration; the rule's configured name and priority were not provided. `Allow-HTTP-80` — inbound Allow, TCP/80, source `Any`, priority `320`, for public website traffic. There is no public inbound allow rule for TCP/8000.
- **Redaction reminder:** Before committing or pushing this plan, remove sensitive information such as the laptop public IP and Azure subscription ID. Neither is included in this execution record.
- **Scope:** No Azure networking rules were changed; port 443 was not opened. Sections 4 and 5 are recorded. The SSH address and Azure subscription ID are not included.
