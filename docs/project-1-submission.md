# Project 1: Own Your Corner of the Internet

**Course:** LMU ISBA 4775
**Due:** October 22, 2026, 1:45 PM Pacific
**Rubric total:** 125 points

> This index separates repository evidence from historical observations and outstanding evidence. A plan, test, or screenshot is not proof of current production behavior unless stated. No migration or test execution is claimed here.

## Final submission details

- **Repository URL:** https://github.com/ariddick195/career-platform
- **Live HTTPS URL:** https://adamriddick.me - HTTPS returned successfully during read-only checks, but the current hosting platform and Railway cutover have not been verified.
- **Current local and GitHub commit SHA:** `d16e2599c07c1755ed60d36a9d925311485e6c3c` - the local `main` branch was reported up to date with `origin/main`; the deployed revision has not been verified.

## Rubric evidence index

### 1. Personal application - 15 points - **PARTIAL**

- **VERIFIED (source present):** Application and database-backed profile/project reads are implemented in [`main.py`](../main.py) and [`db_schema.py`](../db_schema.py), consistent with the [original career-platform specification](superpowers/specs/2026-09-15-personal-resume-career-platform-design.md).
- **VERIFIED (unit tests, run October 23, 2026):** [`tests/test_admin_security_and_home.py`](../tests/test_admin_security_and_home.py) now covers a healthy homepage (HTTP 200), an all-tables-empty database (HTTP 200, no sample projects), a database failure (HTTP 503, last real profile still shown, "Projects temporarily unavailable"), and recovery on the next refresh without a restart. Full suite: 52 tests passed, 1 skipped.
- **GAP:** The 503 behavior has not yet been checked on the live deployment.

### 2. Azure - 20 points - **PARTIAL**

- **VERIFIED (historical):** Azure migration record and deployment screenshot: [`docs/evidence/ex03.md`](evidence/ex03.md) and [`ex03-site.png`](evidence/ex03-site.png). The screenshot is dated October 1, 2026 and shows the public IP over HTTP on port 8000, marked "Not secure"; it does not establish current HTTPS or current deployment state.
- **VERIFIED (dated execution record):** Service, two-worker, socket, and network-rule observations are recorded in the October 8 execution record: [`2026-10-01-operate-the-vm.md`](superpowers/plans/2026-10-01-operate-the-vm.md). These are not a current Azure inspection.
- HTTPS and network documentation: [`docs/how-this-site-is-secured.md`](how-this-site-is-secured.md).
- **GAP:** No evidence of service persistence after a VM restart. Reconfirm current worker count, boot enablement, socket binding, and NSG rules before claiming the current state.

### 3. Domain/HTTPS - 15 points - **GAP**

- **VERIFIED (read-only check, October 21, 2026):** HTTPS GET requests to `https://adamriddick.me/`, `https://www.adamriddick.me/`, and `/privacy` on both hosts returned HTTP 200; curl reported TLS verification result 0. The `www` URL remained on `www` after redirects were followed, so the required redirect to the bare domain is not present in this check.
- **VERIFIED (historical Azure evidence only):** Domain, certificate, redirect, and renewal notes: [`docs/how-this-site-is-secured.md`](how-this-site-is-secured.md).
- **VERIFIED (browser capture dated October 20, 2026):** The captures show `www.adamriddick.me` over HTTPS while inspecting analytics requests: [`page_view capture`](evidence/screenshots/Screenshot%202026-10-20%20190101.png) and [`outbound-click capture`](evidence/screenshots/Screenshot%202026-10-20%20190327.png). They do not establish Railway routing or current behavior.
- **GAP:** The live HTTPS check does not identify the serving platform. No evidence establishes that the final bare domain points to Railway, that `www` redirects correctly, or that a Railway certificate renews. The existing HTTPS document describes Azure.

### 4. Railway/PostgreSQL migration - 25 points - **GAP**

- **VERIFIED (artifacts present):** Migration design and implementation plan: [`2026-10-13-railway-postgresql-migration-design.md`](superpowers/specs/2026-10-13-railway-postgresql-migration-design.md) and [`2026-10-13-railway-postgresql-migration.md`](superpowers/plans/2026-10-13-railway-postgresql-migration.md).
- **VERIFIED (procedure only):** [`docs/railway-migration-runbook.md`](railway-migration-runbook.md) documents how to migrate; it does not establish that a production migration occurred.
- **VERIFIED (source present, not executed here):** Schema, transfer tool, and transfer-test source: [`migrations/versions/0001_initial_schema.py`](../migrations/versions/0001_initial_schema.py), [`scripts/transfer_database.py`](../scripts/transfer_database.py), and [`tests/test_database_transfer.py`](../tests/test_database_transfer.py).

**CURRENT BLOCKER:** Railway CLI authentication is working (`railway.cmd whoami` succeeds), and the registered staging SSH key is recognized. However, the SSH connection to `ssh.railway.com` on port 22 times out, so no private tunnel or target database connection has been established. The local variable name `RAILWAY_DATABASE_URL` does not match the transfer utility's expected `DATABASE_URL`; its value was not read or used, and the intended target remains unverified. Do not use it as the import target without independently identifying and verifying the target.
### 5. Verified website update - 5 points - **GAP**

- **VERIFIED (repository history):** Relevant repository commits include `0e1c226` (Railway/PostgreSQL foundations), `2c4dca4` (migration runbook), `ffd6811` (privacy page and analytics consent), `3b4d886` (outbound analytics clicks), and `7d4505f` (Exercise 06 evidence/screenshots).
- **GAP:** No reviewed commit SHA is linked to a Railway deployment and verified live behavior. Fill the final SHA above only after checking the deployed revision and live site.

### 6. Zoho email - 15 points - **PARTIAL**

- Recorded email observations and authentication results: [`docs/evidence/ex06.md`](evidence/ex06.md).
- **VERIFIED (one outgoing message):** "Test 04" delivery and SPF/DKIM/DMARC pass are shown in [`Original Script.png`](evidence/screenshots/Original%20Script.png). This is evidence for that outgoing message, not a complete DNS/MX record inventory.
- **PARTIAL (written observations only):** Incoming and reply outcomes are recorded in the evidence note, but the reply is not established as part of the recorded incoming thread and supporting captures are absent.
- **GAP:** No before-MX test or MX-record evidence is indexed.

**Evidence screenshots:**
- `docs/evidence/screenshots/Original Script.png` - Test 04 message details showing delivery and SPF, DKIM, and DMARC passing.
- `docs/evidence/screenshots/Excercise 6 evidence.png` - Test 04 message visible in the Gmail inbox.

### 7. GA4 - 10 points - **PARTIAL**

- **VERIFIED (browser Network captures dated October 20, 2026):** Page-view request: [`October 20 page_view capture`](evidence/screenshots/Screenshot%202026-10-20%20190101.png); outbound-click request and payload: [`October 20 outbound-click capture`](evidence/screenshots/Screenshot%202026-10-20%20190327.png).
- Evidence summary and implementation: [`docs/evidence/ex06.md`](evidence/ex06.md), [`static/analytics-consent.js`](../static/analytics-consent.js), and [`tests/analytics-consent.test.js`](../tests/analytics-consent.test.js).
- **GAP:** The screenshots show browser Network requests, not receipt in GA4 Realtime or DebugView. No property-level verification is included. Consent tests were not run for this record.

**Additional verification (October 21, 2026):** GA4 Realtime showed zero active users after visiting the website. The browser Network panel showed zero requests matching the `collect` filter during the subsequent check. The October 20 screenshots document browser-side analytics requests, but successful receipt by GA4 remains unverified.

### 8. Engineering Record - 20 points - PARTIAL

- Project setup and deployment instructions: [`README.md`](../README.md).
- **VERIFIED (documents present):** Original application specification and plans: [`2026-09-15-personal-resume-career-platform-design.md`](superpowers/specs/2026-09-15-personal-resume-career-platform-design.md), [`2026-09-22-personal-resume-career-platform-plan.md`](superpowers/plans/2026-09-22-personal-resume-career-platform-plan.md), [`2026-09-24-azure-vm-migration.md`](superpowers/plans/2026-09-24-azure-vm-migration.md), [`2026-10-01-operate-the-vm.md`](superpowers/plans/2026-10-01-operate-the-vm.md), and the Railway design/plan linked above.
- Failure investigation: [`docs/evidence/ex05.md`](evidence/ex05.md). It explicitly records a supplied simulation, not a repair to the personal live site.

The repository URL, live HTTPS URL, and current local commit SHA are recorded above. The deployed revision and current hosting platform remain unverified.
