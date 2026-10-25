# Adam Riddick Career Platform

A database-driven personal resume and career website. Profile, education, experience, projects, skills, certifications, volunteer work, and links are stored in a database and read on every page request.

- **Live site:** <https://adamriddick.me> (`www.adamriddick.me` redirects here)
- **Hosting now:** Railway web service + Railway PostgreSQL (since October 23, 2026)
- **Hosting before:** Azure Ubuntu VM with Nginx, Uvicorn, systemd, and SQLite (kept running as the rollback target)
- **Email:** `adamriddick@adamriddick.me` on Zoho Mail
- **Analytics:** Google Analytics 4, loaded only after the visitor accepts analytics
- **Evidence index:** [docs/project-1-submission.md](docs/project-1-submission.md)

> This README was rewritten on October 25, 2026, after the Railway cutover, to describe the system as it runs now. The Azure section is kept as history. The migration plan itself was written before the cutover: see [the Railway design](docs/superpowers/specs/2026-10-13-railway-postgresql-migration-design.md) and [plan](docs/superpowers/plans/2026-10-13-railway-postgresql-migration.md).

## Contents

1. [What the site does](#what-the-site-does)
2. [Run it locally](#run-it-locally)
3. [How it runs on Railway and how to update it](#how-it-runs-on-railway-and-how-to-update-it)
4. [Rollback](#rollback)
5. [Architecture diagrams](#architecture-diagrams)
6. [Migration: how current data was preserved](#migration-how-current-data-was-preserved)
7. [Who manages what: Azure vs Railway](#who-manages-what-azure-vs-railway)
8. [Decisions](#decisions)
9. [Investigated failures](#investigated-failures)
10. [Remaining limitations](#remaining-limitations)
11. [Costs, expiration dates, and cleanup](#costs-expiration-dates-and-cleanup)
12. [Reflection](#reflection)

## What the site does

- The homepage reads every profile section from the database on each request.
- If the database cannot be reached, the page keeps the last profile it read, shows **"Projects temporarily unavailable,"** and returns **HTTP 503**. The next refresh after the database recovers shows the projects again with HTTP 200, without an application restart. No sample content is substituted. ([`main.py`](main.py), tests in [`tests/test_admin_security_and_home.py`](tests/test_admin_security_and_home.py))
- An empty database returns HTTP 200 with no invented projects.
- `/privacy` explains analytics collection. A consent banner and a **Privacy settings** footer button let visitors accept, reject, or withdraw analytics; the site works fully when analytics is rejected.
- `/admin` is a small content editor behind HTTP Basic authentication. Writes require an exact allowed origin. If admin credentials are not configured, the public site still works and `/admin` returns 503.

Application stack: Python, FastAPI, Jinja templates, SQLAlchemy Core, Alembic migrations. Original design: [specification](docs/superpowers/specs/2026-09-15-personal-resume-career-platform-design.md) and [implementation plan](docs/superpowers/plans/2026-09-22-personal-resume-career-platform-plan.md).

## Run it locally

Python 3.11 or newer is required (the code uses `X | None` type syntax).

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Windows PowerShell: Copy-Item .env.example .env
# Linux/macOS: cp .env.example .env
alembic upgrade head
python -m scripts.seed_dev
uvicorn main:app --reload --env-file .env
python -m unittest discover -s tests
```

Local development uses SQLite at `data/career-platform.db` with `APP_ENV=development`. Alembic creates the schema; `scripts.seed_dev` adds example content only in development against an empty SQLite database. Application startup never creates or seeds a database, and the seed command refuses to run in production.

For local admin access, set non-empty `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`, then open <http://127.0.0.1:8000/admin>.

## How it runs on Railway and how to update it

| Setting | Value |
|---|---|
| Railway project / environment | `secure-analysis` / `staging` |
| Web service | `mindful-creativity`, deployed from GitHub `ariddick195/career-platform`, branch `main` |
| Database | `Postgres-UR2d` (Railway PostgreSQL) |
| Generated URL | <https://mindful-creativity-staging.up.railway.app> |
| Custom domain | `adamriddick.me`, port 8080 |
| Variables | `APP_ENV=production`, `DATABASE_URL` as a Railway reference to the Postgres service, and `ADMIN_*` only when admin writes are enabled. Values live in Railway, never in Git. |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` (Railway supplies `PORT`) |

In production the app requires a PostgreSQL `DATABASE_URL` and fails closed without one; it never falls back to SQLite.

**To publish a change:**

1. Make the change locally, review `git diff`, and run `python -m unittest discover -s tests`.
2. Commit and push to `main`. Railway builds and deploys that commit automatically.
3. In Railway > Deployments, find the same commit message and SHA and wait for **Deployment successful**.
4. Check the live site: `curl.exe -si https://adamriddick.me` should return `200 OK` with an `x-railway-request-id` header.

**Schema changes** are Alembic migrations (`migrations/versions/`). Apply them to Railway PostgreSQL with `alembic upgrade head` before relying on the new code. Never run `scripts.seed_dev` against production.

Verified example: commit `ae000c0` (the 503 database-failure behavior) was reviewed and tested locally, deployed by Railway on October 23, 2026, and serves the live domain ([evidence](docs/evidence/railway-migration.md#7-verified-website-update)). Commit `0c5c65f` (GA4 ID fix) followed the same path on October 25.

## Rollback

Rolling back code and rolling back data are different problems.

**Code (a bad deploy):**
- Fastest: Railway > Deployments > the last good deployment > **Redeploy**.
- Permanent: `git revert <bad-commit>` and push to `main`; Railway deploys the revert.

**Database schema:** `alembic downgrade -1` reverts the last migration. Take a Railway PostgreSQL backup (Backups tab) first, because a downgrade can drop columns and their data.

**Data or platform (moving back to Azure):** Since cutover, Railway PostgreSQL has taken at least one write that Azure does not have (the LinkedIn link fix). Pointing DNS back to Azure alone would serve stale data. The procedure, detailed in the [runbook](docs/railway-migration-runbook.md#rollback):

1. Stop admin writes on Railway.
2. Back up Railway PostgreSQL.
3. Export it to a **new** SQLite file: `python -m scripts.transfer_database --direction postgres-to-sqlite --sqlite-path <new-file>.db`, with `DATABASE_URL` set to the Railway database for that one command. Verify all eight table counts.
4. Install that file on the Azure VM as `/var/lib/career-platform/career-platform.db`, keeping the old file, then restart `career-platform`.
5. In Cloudflare, set the root record back to **A `adamriddick.me` -> `9.205.27.2`**, DNS only. The Azure Let's Encrypt certificate covers `adamriddick.me` and `www`.
6. Check HTTPS and the page content on Azure before re-enabling writes.

## Architecture diagrams

### Azure (September 24 to October 23, 2026)

```text
Visitor browser
   |  DNS: Cloudflare (DNS only)  adamriddick.me  A  9.205.27.2
   v
Azure public IP 9.205.27.2  ->  NSG: 22 from my laptop /32 only, 80 and 443 from Any
   v
Ubuntu VM vm-career-platform (private IP 172.16.0.4, Denmark East)
   ├─ sshd :22
   ├─ Nginx :80   -> 301 redirect to HTTPS
   ├─ Nginx :443  TLS ends here (Let's Encrypt certificate, Certbot renewal timer)
   │      | plain HTTP over loopback
   │      v
   │  Uvicorn 127.0.0.1:8000, 2 workers, run by systemd as azureuser
   │      | local file access
   │      v
   │  SQLite /var/lib/career-platform/career-platform.db
```

### Railway (since October 23, 2026), with email and analytics

```text
                     Cloudflare DNS for adamriddick.me
   @    CNAME -> kvovk0pv.up.railway.app   (currently Proxied, see limitations)
   www  CNAME -> adamriddick.me, Proxied   + redirect rule: 301 to https://adamriddick.me/
   MX   mx.zoho.com / mx2 / mx3            TXT: SPF, DKIM (zoho._domainkey), DMARC, Zoho + Railway verification

WEB REQUEST
Visitor browser --HTTPS 443--> Cloudflare edge --HTTPS--> Railway edge (TLS, routing)
                                                              | HTTP, PORT 8080
                                                              v
                                       web service mindful-creativity (Uvicorn + FastAPI)
                                                              | PostgreSQL protocol, Railway private network
                                                              v
                                                     Postgres-UR2d (Railway volume)

ANALYTICS (only after the visitor accepts)
Visitor browser --HTTPS--> googletagmanager.com (loads gtag.js, ID G-D1DVSBC3WV)
Visitor browser --HTTPS--> google-analytics.com/g/collect  (page_view, click with link_url, outbound)
                                     v
                           GA4 property adamriddick.me (Realtime / DebugView)

EMAIL
Inbound:  sender's mail server --DNS MX lookup--> mx.zoho.com --SMTP 25--> Zoho mailbox --HTTPS--> Zoho webmail
Outbound: Zoho webmail --> Zoho SMTP --SMTP--> recipient server (e.g. Gmail)
          recipient checks SPF (TXT @), DKIM (TXT zoho._domainkey), DMARC (TXT _dmarc) in Cloudflare DNS
```

## Migration: how current data was preserved

The plan was written before any change to the working Azure deployment: [design](docs/superpowers/specs/2026-10-13-railway-postgresql-migration-design.md), [plan](docs/superpowers/plans/2026-10-13-railway-postgresql-migration.md), [runbook](docs/railway-migration-runbook.md).

**What Git moves:** application code, templates, static files, the Alembic schema, `requirements.txt`/`uv.lock`, and tests. **What Git does not move:** secrets (Railway variables), the database rows (transfer utility), and DNS (Cloudflare, by hand).

**PostgreSQL compatibility changes:** SQLite-specific `sqlite3` calls and `?` placeholders were replaced with SQLAlchemy Core and named parameters; table creation at import was replaced by Alembic migrations; production requires PostgreSQL and never seeds; the app binds to `0.0.0.0:$PORT`. ([commit `0e1c226`](https://github.com/ariddick195/career-platform/commit/0e1c226))

**Data transfer:** `scripts/transfer_database.py` imports all eight tables from a SQLite snapshot into an empty, migrated PostgreSQL database in one transaction, preserving IDs and `person_id` relationships and advancing sequences. Verified Azure source counts: person 1, education 1, experience 1, project 3, skill 4, certification 3, volunteer_experience 3, link 4.

**Proof it is current data, not seed data:** the Azure database had a placeholder LinkedIn URL; the development seed has the real URL. After cutover I changed the LinkedIn URL in Railway PostgreSQL and saw it on the live site. Row counts and screenshots: [railway-migration.md](docs/evidence/railway-migration.md#2-current-data-comparison) (**partly pending**).

**Cutover (October 23, 2026):** before/after DNS and HTTP checks, the TLS failure, and the `www` redirect are in [railway-migration.md](docs/evidence/railway-migration.md). Azure stays running.

**What moved to Railway (compared with the Azure HTTPS work in Exercise 04):** on Azure, HTTPS took a port 443 NSG rule, Nginx `server_name`, Certbot, a domain challenge, and a renewal timer. On Railway it took one custom domain entry and two DNS records, because Railway runs the edge, TLS, and routing for me.

## Who manages what: Azure vs Railway

| Layer | Azure VM | Railway |
|---|---|---|
| Hardware, hypervisor, network | Azure | Railway |
| Operating system and patches | **Me** (Ubuntu) | Railway |
| Language runtime (Python) | **Me** (venv on the VM) | Railway builds it; **I** choose the version and dependencies |
| Web entry point | **Me** (Nginx, NSG rules) | Railway edge |
| TLS certificate and renewal | **Me** (Certbot, renewal timer) | Railway (Let's Encrypt), **I** keep DNS correct |
| Process management | **Me** (systemd, 2 Uvicorn workers) | Railway restarts the container; **I** set the start command |
| Application code | **Me** | **Me** |
| Configuration and secrets | **Me** (`.env` on the VM) | **Me** (Railway variables) |
| Database software | **Me** (SQLite file) | Railway runs PostgreSQL but calls it unmanaged |
| Data, schema, backups, restores | **Me** | **Me** |
| DNS | **Me** (Cloudflare) | **Me** (Cloudflare) |
| Testing, monitoring, recovery | **Me** | **Me** |

PaaS is not maintenance-free: Railway took the OS, runtime host, edge, and certificate work, but my code, settings, secrets, schema, data, backups, DNS, and verification are still mine.

## Decisions

> Drafted October 25, 2026, from the class discussions. **Adam: rewrite these in your own words before submitting.**

### Decision 1: Move from the Azure VM to Railway

*Scenario:* CTO of a three-developer startup running on an Azure VM; Railway offers to take over the infrastructure.

- **Alternatives:** stay on the Azure VM; move to Railway; another PaaS.
- **Recommendation:** move to Railway for the current stage.
- **Why:** On Azure, every deploy was SSH, pull, sync, restart, and HTTPS took five manual pieces. On Railway a push to `main` deploys, and the platform handles the OS, edge, and certificates. For three developers, hours saved on server upkeep are worth more than the platform's price at this traffic.
- **Costs and risks:** less control (no Nginx tuning, no shell on the host); Railway's trial ends in 30 days or $5, and the Free plan has no custom domain, so it becomes a paid service; PostgreSQL backups are still our job.
- **What would change my answer:** high, steady traffic where a VM is cheaper; strict compliance needing control of the host; or Railway outages affecting customers.

### Decision 2: Managed email (Zoho) instead of my own mail server

- **Alternatives:** run Postfix/Dovecot on the VM; use Zoho Mail free plan; Google Workspace.
- **Choice:** Zoho Mail.
- **Why:** Zoho runs the mail servers, spam filtering, storage, and sender reputation. A new self-hosted server's IP would likely be distrusted, and port 25 is often blocked on cloud VMs. Setup was a few DNS records.
- **What I still own:** the MX, SPF, DKIM, and DMARC records and the evidence they work. One wrong record means lost or spam-foldered mail.
- **What would change my answer:** needing IMAP clients (free plan has none) or more mailboxes would mean a paid plan; self-hosting only makes sense with dedicated email expertise.

### Decision 3: SQLite on Azure, PostgreSQL on Railway

SQLite fit a single VM: one file, no server, and the app and database on the same disk. On Railway each push replaces the app container, so a database file inside it would be lost on the next deploy; a separate PostgreSQL service keeps the data independent of deploys and is what the course requires. SQLite stays for local development.

## Investigated failures

| # | Type | Failure | Record |
|---|---|---|---|
| 1 | Application/dependency | App would not start on the VM: no checkout, then a `.env` with a UTF-8 byte-order mark broke `DATA_DIR` | [ex03.md](docs/evidence/ex03.md) |
| 2 | DNS/TLS (**supplied simulation**) | Hostname still pointed to the old server, so the certificate name did not match | [ex05.md](docs/evidence/ex05.md) |
| 3 | TLS (real, cutover) | After switching to DNS only: `SEC_E_WRONG_PRINCIPAL`; Railway hit the Let's Encrypt rate limit. Temporary fix: proxied through Cloudflare | [railway-migration.md §5](docs/evidence/railway-migration.md#5-investigated-failure-tls-certificate-after-switching-to-dns-only) |
| 4 | Analytics config (real) | GA4 received nothing: the site used `G-D1DVSB3CWV`, the property is `G-D1DVSBC3WV`. Fixed in `0c5c65f`, verified in Realtime | [ex06.md](docs/evidence/ex06.md#investigated-failure-events-never-reached-my-ga4-property) |
| 5 | Application behavior | Homepage returned 200 with an empty page when the database failed; changed to 503 with the last profile and a message | Commit `ae000c0`, tests |

Each record gives the symptom, the checks, the diagnosis, the repair, and the repeated check.

## Remaining limitations

- **Root record is Proxied, not DNS only.** Railway's certificate request hit the Let's Encrypt rate limit; visitors currently get Cloudflare's certificate. Retry plan in [railway-migration.md §5](docs/evidence/railway-migration.md#5-investigated-failure-tls-certificate-after-switching-to-dns-only).
- **Azure restart evidence** (controlled reboot, service comes back) has not been recorded; the October 8 record covers service setup only.
- **Data comparison** row counts and some Railway screenshots are still pending.
- **Before-MX email test** is not yet recorded in [ex06.md](docs/evidence/ex06.md).
- **`www`** is served only by the Cloudflare redirect; Railway's trial allows one custom domain.
- **Admin writes on Railway** stay disabled until `ADMIN_ALLOWED_ORIGINS` and production credentials are set.
- **Trial clock:** Railway has 20 days or $4.67 left as of October 23, 2026.

## Costs, expiration dates, and cleanup

| Service | What it is | Cost / plan | Expires or renews | Cleanup plan |
|---|---|---|---|---|
| Railway | Web service + PostgreSQL | Trial ($5 credit) | About **November 12, 2026** (20 days or $4.67 left on Oct 23) | Migrate to AWS after the midterm, before the trial ends |
| Azure VM `vm-career-platform` | Compute (Standard_B2ts_v2, Denmark East) | Student credits | While credits last | After the instructor says so: Stop (deallocate) to stop compute charges |
| Azure disk + static public IP | Retained storage and IP | Charge even when the VM is stopped | Same | Delete with the resource group `rg-career-platform` when told |
| Domain `adamriddick.me` | Namecheap registration | Paid yearly (**Adam: add price**) | **Adam: add renewal date** | Keep; it is my email address too |
| Cloudflare | DNS, redirect rule | Free | n/a | Keep |
| Zoho Mail | `adamriddick@adamriddick.me` | Forever Free (1 domain, 5 users, 5 GB, no IMAP) | n/a | Keep |
| Google Analytics 4 | Analytics | Free | n/a | Keep |
| Let's Encrypt (Azure) | Certificate on the VM | Free | Expires Jan 6, 2027; Certbot renews | Ends with the VM |

## Reflection

> **Adam: write this yourself (3 to 5 sentences).** Prompts: What do you understand now that you did not in September (for example, why DNS-only vs proxied matters, or why a 503 is better than a blank 200)? What would you do differently (for example, double-check IDs copied from dashboards, take before/after evidence as you go, avoid one-click setups that hide what changes)?
