# Azure VM Migration Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to carry out these steps task-by-task. Steps use checkbox syntax for tracking. Do not run this plan until the user asks to execute it.

**Goal:** Deploy the FastAPI career platform to the existing Azure VM and serve it using the user's SQLite database.

**Architecture:** Clone the application from GitHub into the VM user's home directory, install its locked Python dependencies with `uv`, and run Uvicorn with configuration from `.env`. Store the SQLite database in a persistent data directory outside the Git checkout; verify the app and data before removing temporary network access.

**Tech Stack:** Azure Ubuntu VM, SSH/SCP, apt-get, Git, `uv`, Python, FastAPI, Uvicorn, Jinja2, plain CSS, SQLite.

**Spec:** User-provided ordered migration sequence in this conversation. No separate design spec.

## Global Constraints

- Target VM: `vm-career-platform` in resource group `rg-career-platform`.
- Target public IP: `9.205.27.2`; SSH user: `azureuser`; private key: `~/.ssh/isba4775_azure` for every SSH or SCP connection.
- Run commands only where indicated; portal steps are Azure Portal actions.
- Preserve the laptop database and make a VM-side backup before replacing an existing database.
- Do not commit `.env`, secrets, or SQLite database files.
- Do not expose SSH or the temporary Uvicorn port to all source addresses.

## Files and Inputs

- Modify before deployment: `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, and application configuration as needed so the VM can use the lock file and `.env` settings.
- Deploy: `main.py`, `templates/`, `static/`, and the packaging/configuration files from the selected GitHub commit.
- Preserve on the VM: `/var/lib/career-platform/career-platform.db`.
- User inputs still needed at execution: `<GITHUB_REPOSITORY_URL>`, `<LAPTOP_DB_PATH>`, and the laptop's current public IP for a restricted temporary NSG rule.

## Review Focus

- Wrong SSH destination or key: check VM identity, public IP, and `whoami` before changing it.
- Incomplete/unlocked deployment commit: check the target commit includes `pyproject.toml`, `uv.lock`, and `.env.example`.
- Incorrect or incompatible laptop database: check SQLite integrity and expected table/column schema before transfer.
- Existing VM database overwritten: make a timestamped backup before installation and document restore commands.
- App cannot find or write the deployed DB: check the effective `DATA_DIR`, file ownership, and a reversible admin write.

---

## Server

### Task 1: Confirm the Azure target and SSH access

**Interfaces:** Uses the already-created Azure VM. Produces a confirmed VM shell as `azureuser` for later tasks.

- [x] **Step 1: Confirm VM state and SSH rule**
  - **Where:** Portal (Azure Portal).
  - **What:** Open resource group `rg-career-platform` → VM `vm-career-platform`. Confirm it is running and its public IP is `9.205.27.2`. In Networking, confirm inbound TCP 22 is allowed only from the laptop's current public IP; add a source-restricted rule if needed.
  - **Why:** Confirm the selected VM and avoid opening administrative SSH to the internet.
  - **Check:** VM Overview shows the specified resource, state, and public IP; its NSG has the restricted SSH rule.
  - **Undo:** Remove only an SSH rule added for this task. Leave pre-existing VM and network resources intact.

- [x] **Step 2: Open and identify the SSH session**
  - **Where:** Laptop.
  - **What:** Run `ssh -i ~/.ssh/isba4775_azure azureuser@9.205.27.2`, then run `hostname` and `whoami` in the VM shell.
  - **Why:** Validate the required SSH user/key and confirm the remote shell is on the intended VM.
  - **Check:** SSH succeeds, `whoami` prints `azureuser`, and the hostname identifies the career platform VM.
  - **Undo:** Run `exit` to close the session; this makes no server changes.

## Packages

### Task 2: Install the requested Ubuntu packages

**Interfaces:** Consumes the SSH session from Task 1. Produces `git` and `sqlite3` on the VM.

- [x] **Step 1: Install Git and SQLite CLI**
  - **Where:** VM (SSH shell).
  - **What:** Run `sudo apt-get update` followed by `sudo apt-get install -y git sqlite3`.
  - **Why:** Install the packages specified for cloning source and inspecting the transferred database.
  - **Check:** `git --version` and `sqlite3 --version` each print a version and exit successfully.
  - **Undo:** If no other VM workload needs them, run `sudo apt-get remove git sqlite3`. This does not remove the app or its database.

## Code

### Task 3: Publish a deployable Python project and clone it on the VM

**Interfaces:** Consumes the current app in this repository. Produces a GitHub commit with Python packaging and deployment configuration, then a clean VM clone at `/home/azureuser/career-platform`.

- [x] **Step 1: Add `uv` project metadata and lock file**
  - **Where:** Laptop (project checkout).
  - **What:** Add `pyproject.toml` declaring the app's runtime dependencies (FastAPI, Uvicorn, Jinja2, and `python-multipart`, consistent with `requirements.txt`); generate and commit `uv.lock`. Keep `requirements.txt` only if it remains useful for non-`uv` installs.
  - **Why:** The current checkout has `requirements.txt` but no `pyproject.toml` or `uv.lock`; `uv sync --frozen` cannot run until those files are committed.
  - **Check:** `uv lock --check` succeeds and a clean checkout can run `uv sync --frozen`.
  - **Undo:** Revert the packaging changes with Git if they are incorrect; do not remove the existing `requirements.txt` until the lock-file install works.

- [x] **Step 2: Add environment template and ignore local data**
  - **Where:** Laptop (project checkout).
  - **What:** Add `.env.example` with supported, non-secret settings, including `DATA_DIR=/var/lib/career-platform`. Ensure `.gitignore` excludes `.env`, `.venv/`, and database files. The app's startup command must load `.env` (for example, use `uv run --env-file .env`) because `main.py` currently reads environment variables but does not load dotenv files itself.
  - **Why:** Make the requested `.env` copy effective and keep private configuration and local databases out of Git.
  - **Check:** `.env.example` is tracked; `.env`, `.venv/`, and the local `.db` file are ignored; `uv run --env-file .env` exposes `DATA_DIR` to the app process.
  - **Undo:** Revert only the template/ignore changes as needed. Preserve any local `.env` or database before cleanup.

- [x] **Step 3: Commit and push the deployable version**
  - **Where:** Laptop (project checkout and GitHub).
  - **What:** Commit the app, `pyproject.toml`, `uv.lock`, `.env.example`, and `.gitignore` changes, then push to the GitHub repository intended for this VM.
  - **Why:** The VM clone must contain the locked Python project and supported configuration.
  - **Check:** The pushed commit is visible in GitHub and contains all required files; `.env` and SQLite DB are absent.
  - **Undo:** Revert the commit with a new commit if it should not be deployed; avoid rewriting shared history.

- [x] **Step 4: Clone the selected GitHub repository**
  - **Where:** VM (SSH shell).
  - **What:** Check whether `/home/azureuser/career-platform` already exists. If it does not, run `git clone <GITHUB_REPOSITORY_URL> /home/azureuser/career-platform`. If it exists, inspect it and choose a new empty deployment path rather than overwriting unknown contents.
  - **Why:** Put the pushed application version on the VM while preserving any existing data.
  - **Check:** `git -C /home/azureuser/career-platform status --short` is empty and `git -C /home/azureuser/career-platform rev-parse --short HEAD` reports the intended commit.
  - **Undo:** If this task created a fresh clone and it contains no user data, remove only that confirmed clone directory. Otherwise leave it intact and use a separate deployment directory or revert with Git.

## Python

### Task 4: Install `uv` and sync the locked environment

**Interfaces:** Consumes the clone and committed lock file from Task 3. Produces an installed project environment under `.venv/`.

- [x] **Step 1: Install `uv` for `azureuser`**
  - **Where:** VM (SSH shell).
  - **What:** Install `uv` for the `azureuser` account using Astral's official `uv` installer instructions; start a fresh shell if required so the installed binary is on `PATH`.
  - **Why:** Provide the package manager requested for reproducible project setup.
  - **Check:** `uv --version` prints the installed version.
  - **Undo:** Remove the user-level `uv` executable using the installer’s documented uninstall/removal procedure; this does not change project source or database files.

- [x] **Step 2: Sync exactly from the lock file**
  - **Where:** VM (SSH shell).
  - **What:** Run `cd /home/azureuser/career-platform` and `uv sync --frozen`.
  - **Why:** Install dependencies matching the committed lock file without changing it on the VM.
  - **Check:** The command exits successfully and `/home/azureuser/career-platform/.venv/bin/python` exists.
  - **Undo:** Stop any app process, then remove only the confirmed project `.venv/` directory if a clean retry is needed; rerun `uv sync --frozen` to recreate it.

## Config

### Task 5: Create the VM environment file

**Interfaces:** Consumes `.env.example` from the deployment commit. Produces a private VM `.env` that the Uvicorn command loads.

- [x] **Step 1: Copy and set deployment values**
  - **Where:** VM (SSH shell).
  - **What:** From the project root, run `cp .env.example .env`, edit `.env` to set VM-specific values (including `DATA_DIR=/var/lib/career-platform`), and run `chmod 600 .env`. Do not put secrets in Git or terminal transcripts.
  - **Why:** Configure the process without editing tracked source or exposing credentials.
  - **Check:** `test -f .env` succeeds; `stat -c '%a %n' .env` shows mode `600`; inspect key names without printing secret values.
  - **Undo:** Restore a protected backup of the previous `.env`, or remove only the new `.env` after confirming its path. Never delete or overwrite an existing environment file without a backup.

## Data

### Task 6: Validate, transfer, and install the laptop SQLite database

**Interfaces:** Consumes the app schema and `.env` database path. Produces `/var/lib/career-platform/career-platform.db` on the VM, with a rollback copy if VM data existed.

- [x] **Step 1: Identify and back up the laptop database**
  - **Where:** Laptop.
  - **What:** Set `<LAPTOP_DB_PATH>` to the intended SQLite file. Confirm the file exists and inspect its tables and current profile. Before changing any records, use Python's `sqlite3.Connection.backup()` to create a sibling backup named `<LAPTOP_DB_PATH>.before-personalization.bak`.
  - **Why:** Identify the exact source database and preserve its original contents before replacing the seeded career records.
  - **Check:** The source file and backup both exist, the backup is non-empty, and the inspected schema includes `person`, `education`, `experience`, `project`, `skill`, `certification`, `volunteer_experience`, and `link`.
  - **Undo:** Restore the backup to `<LAPTOP_DB_PATH>` if personalization needs to be rolled back. Do not proceed if the intended database or backup is uncertain.

- [x] **Step 2: Replace the approved career records in the laptop database**
  - **Where:** Laptop.
  - **What:** In a SQLite transaction, update the existing profile to Adam Riddick, Los Angeles, CA, USA, and `ariddick@lion.lmu.edu`; set the career goal to “Information Systems and Business Analytics student seeking opportunities in supply chain and business analytics,” leave `phone` empty, and retain the existing LinkedIn link. Replace the education, experience, project, and skill rows with the following resume data:
    - Education: Loyola Marymount University, Los Angeles, CA; B.A. in Information Systems and Business Analytics; August 2023–May 2027; coursework in Analytics in Operations and Supply Chain Management, Programming for Business Applications, and Database Management Systems.
    - Experience: LMU Distribution Center, Shipping and Receiving Assistant, Los Angeles, CA; July 2024–Present. Record five achievements: processed 250+ departmental orders weekly across nearly 200 campus departments and 25 buildings at approximately 0.02% error; used Intra to process and track about 50 departmental orders per hour during delivery operations; handled up to 160 student packages per day during a two-week move-in period with organized tracking; trained 6+ student hires on inventory software, order procedures, and delivery protocols; assisted evaluation of linear, nonlinear, and modified time-tracking models for employee package retrieval times.
    - Projects: Warehouse Location Optimization Analysis (Excel Solver transportation cost model; 3 factories, 4 warehouse destinations, 400 units of demand; $200 difference between two candidate warehouse locations); BMW Sales Graphs (15 years of global sales across 6 regions, analyzed with pandas, Matplotlib, and NumPy); Music Sales Database Analysis (13 SQL queries using joins, aggregate functions, and subqueries against a multi-table music sales database).
    - Skills: Excel & Access (PivotTables, Solver, Data Analysis ToolPak, data cleaning, database queries); Supply Chain Analytics (cost, capacity, and volume optimization); Inventory Management (inventory tracking, organization, and control); Python & MySQL (Intermediate; data ingestion, filtering, aggregation, and visualization).
  - **Why:** Ensure the source database contains the approved resume information before the migration copies it.
  - **Check:** Query the database and confirm the profile has no phone number; the education, experience, projects, and skills match the entries above; and certifications, volunteer experience, and the existing LinkedIn link remain unchanged.
  - **Undo:** Restore `<LAPTOP_DB_PATH>.before-personalization.bak` if any record is incorrect or an out-of-scope table changed.

- [x] **Step 3: Validate the personalized laptop database**
  - **Where:** Laptop.
  - **What:** Run `sqlite3 "<LAPTOP_DB_PATH>" 'PRAGMA integrity_check;'` and `sqlite3 "<LAPTOP_DB_PATH>" '.tables'`; query the updated profile and the five requested data areas.
  - **Why:** Confirm the personalized database is sound and has the expected app schema before transfer.
  - **Check:** Integrity check prints `ok`; all expected tables and columns remain available; queried rows match Step 2, including an empty phone field.
  - **Undo:** Restore the pre-personalization backup if validation fails, then resolve the issue before proceeding.

- [x] **Step 4: Create persistent VM data storage**
  - **Where:** VM (SSH shell).
  - **What:** Run `sudo install -d -o azureuser -g azureuser -m 0750 /var/lib/career-platform`.
  - **Why:** Keep the database outside the Git clone so future code updates do not replace it.
  - **Check:** `ls -ld /var/lib/career-platform` shows owner `azureuser` and mode `drwxr-x---`.
  - **Undo:** If newly created and empty, run `sudo rmdir /var/lib/career-platform`; do not remove a directory containing a database or backup.

- [x] **Step 5: Upload to a temporary filename**
  - **Where:** Laptop.
  - **What:** Run `scp -i ~/.ssh/isba4775_azure "<LAPTOP_DB_PATH>" azureuser@9.205.27.2:/home/azureuser/career-platform-upload.db`.
  - **Why:** Transfer without overwriting the database path used by the app.
  - **Check:** SCP exits successfully; on the VM, `ls -l /home/azureuser/career-platform-upload.db` shows a non-zero file size.
  - **Undo:** If the wrong file was uploaded, remove only the confirmed temporary file on the VM. The laptop source remains unchanged.

- [x] **Step 6: Back up existing VM data, then install the uploaded DB**
  - **Where:** VM (SSH shell).
  - **What:** Confirm no Uvicorn process is using the DB. If `/var/lib/career-platform/career-platform.db` already exists, copy it to a timestamped backup in `/var/lib/career-platform/`. Validate the upload using `sqlite3 /home/azureuser/career-platform-upload.db 'PRAGMA integrity_check;'`, then copy it into the data directory as a temporary file and atomically rename it to `career-platform.db`. Set owner `azureuser:azureuser` and mode `0640`.
  - **Why:** Install the laptop's data while preserving the old VM database for rollback and avoiding a partially copied live DB.
  - **Check:** Integrity check prints `ok`; `sqlite3 /var/lib/career-platform/career-platform.db '.tables'` lists all expected tables; `stat` confirms `azureuser` ownership and mode `640`.
  - **Undo:** If there was an old DB, restore its timestamped backup to the configured DB path. If no old DB existed, move the new DB aside; do not delete it until migration acceptance.

- [x] **Step 7: Remove the temporary upload**
  - **Where:** VM (SSH shell).
  - **What:** After checking the persistent DB, run `rm /home/azureuser/career-platform-upload.db`.
  - **Why:** Avoid retaining an unnecessary second copy of personal data in the VM home directory.
  - **Check:** The temporary path no longer exists and the persistent DB still passes `PRAGMA integrity_check`.
  - **Undo:** Re-upload from the unchanged laptop source if another install attempt is needed; keep the VM backup until acceptance.

## Processes

### Task 7: Start Uvicorn and allow restricted verification traffic

**Interfaces:** Consumes the clone, `.venv`, `.env`, and persistent SQLite DB. Produces an HTTP service on VM port 8000 for verification.

- [x] **Step 1: Start Uvicorn with the VM environment file**
  - **Where:** VM (SSH shell).
  - **What:** From `/home/azureuser/career-platform`, run `uv run --env-file .env uvicorn main:app --host 0.0.0.0 --port 8000` and keep the SSH session open during verification.
  - **Why:** Run the app with the copied configuration and make it reachable for the external check.
  - **Check:** Uvicorn reports application startup complete; in another SSH session, `curl -fsS http://127.0.0.1:8000/` returns the homepage HTML.
  - **Undo:** Press `Ctrl+C` in the attached session. The code and database remain in place.

- [ ] **Step 2: Add temporary restricted inbound access**
  - **Where:** Portal (Azure Portal).
  - **What:** Add an inbound NSG rule for TCP port 8000 with source set to the laptop's current public IP as `/32`; use a distinct name such as `career-platform-verify`.
  - **Why:** Permit the laptop browser check without opening Uvicorn to all internet sources.
  - **Check:** The rule is visible on the VM's effective NSG and has the expected source and port.
  - **Undo:** Delete this temporary rule after external verification or if verification is abandoned.

> Deviation: The temporary TCP 8000 rule used source * rather than a laptop-specific /32; it was removed after external verification.

## Verify

### Task 8: Confirm the public response and restored content

**Interfaces:** Consumes the running Uvicorn process from Task 7. Produces an accepted deployment check and a closed temporary firewall rule.

- [x] **Step 1: Check the site from the laptop**
  - **Where:** Laptop (browser).
  - **What:** Visit `http://9.205.27.2:8000/` and `/admin`.
  - **Why:** Confirm the app responds through the VM's public interface and that the expected pages render.
  - **Check:** Homepage and admin page return successfully; the profile, education, experience, projects, skills, certifications, volunteer entries, and links match the laptop DB.
  - **Undo:** Close the browser. If incorrect data is shown, stop Uvicorn and restore the VM-side database backup before retrying.

- [x] **Step 2: Check HTTP, SQLite, and deployed commit on the VM**
  - **Where:** VM (SSH shell in a second session).
  - **What:** Run `curl -fsS http://127.0.0.1:8000/ >/dev/null`, `sqlite3 /var/lib/career-platform/career-platform.db 'PRAGMA integrity_check;'`, and `git -C /home/azureuser/career-platform rev-parse --short HEAD`.
  - **Why:** Confirm local HTTP response, DB integrity, and deployed source version independently.
  - **Check:** Curl exits successfully, SQLite prints `ok`, and Git reports the intended commit.
  - **Undo:** These are read-only checks; no rollback is needed.

- [x] **Step 3: Remove the temporary port rule**
  - **Where:** Portal (Azure Portal).
  - **What:** Delete the `career-platform-verify` NSG rule for TCP 8000.
  - **Why:** The temporary direct Uvicorn port is only for migration verification.
  - **Check:** The rule no longer appears; the SSH rule remains available.
  - **Undo:** Re-add the same source-restricted rule if another check is required.

**Run-state note:** Uvicorn attached to an SSH session stops when that process/session ends or the VM reboots. Persistent public operation requires a separately approved systemd/reverse-proxy/HTTPS setup and an admin-access decision; that is outside this migration sequence
