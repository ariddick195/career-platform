# Project 1: Own Your Corner of the Internet

**Course:** LMU ISBA 4775 · **Rubric total:** 125 points · **Index updated:** October 25, 2026

This index links to evidence. Each item says whether it is **verified** (checked, with dated output or screenshots), **historical** (true when recorded, not re-checked), or **pending**.

## Submission details

- **Repository:** <https://github.com/ariddick195/career-platform>
- **Live HTTPS site:** <https://adamriddick.me>, served by Railway since October 23, 2026
- **Final commit SHA:** `9b9c2a22c2c2c7f46b3d3dc40cddc8a9a1058aa5`
- **README:** [README.md](../README.md)

## 1. Original spec and plans

- Application design: [2026-09-15 specification](superpowers/specs/2026-09-15-personal-resume-career-platform-design.md)
- Application plan: [2026-09-22 plan](superpowers/plans/2026-09-22-personal-resume-career-platform-plan.md)
- Azure migration plan: [2026-09-24](superpowers/plans/2026-09-24-azure-vm-migration.md)
- Operate the VM plan and execution record: [2026-10-01](superpowers/plans/2026-10-01-operate-the-vm.md)
- Profile security and homepage plan: [2026-10-12](superpowers/plans/2026-10-12-secure-profile-and-strengthen-homepage.md)
- Railway design and plan (written before cutover): [design](superpowers/specs/2026-10-13-railway-postgresql-migration-design.md), [plan](superpowers/plans/2026-10-13-railway-postgresql-migration.md), [runbook](railway-migration-runbook.md)

## 2. Diagrams

Azure and Railway architecture, including the email and analytics paths: [README > Architecture diagrams](../README.md#architecture-diagrams).

## Rubric evidence

### Personal application (15) — verified

- Database-backed profile and project reads: [`main.py`](../main.py), [`db_schema.py`](../db_schema.py).
- Empty table returns 200 with no sample data; database failure returns **503** with the last profile and "Projects temporarily unavailable"; the next refresh recovers without a restart. Unit tests in [`tests/test_admin_security_and_home.py`](../tests/test_admin_security_and_home.py), 52 tests run October 23, 2026. Commit `ae000c0`.
- Live behavior during an actual database outage was not demonstrated in production.

### Azure deployment (20) — verified

- VM build and migration with troubleshooting: [ex03.md](evidence/ex03.md), [screenshot](evidence/ex03-site.png).
- Nginx on port 80, Uvicorn with 2 workers on `127.0.0.1:8000`, systemd service enabled, listening sockets, private and public IPs, NSG rules with SSH limited to my laptop `/32`: [operate-the-vm execution record, October 8](superpowers/plans/2026-10-01-operate-the-vm.md#execution-record--2026-10-08).
- Ports and the encryption boundary: [how-this-site-is-secured.md](how-this-site-is-secured.md).
- Nginx served the live domain on October 23, 2026, before cutover (`Server: nginx/1.24.0 (Ubuntu)`): [railway-migration.md §3](evidence/railway-migration.md#3-before-cutover).
- Controlled restart on October 25, 2026: the VM booted at 23:06:31 UTC and systemd started `career-platform` at 23:06:41 UTC with nobody logged in; Nginx active; the app served my profile: [restart test](superpowers/plans/2026-10-01-operate-the-vm.md#restart-test--2026-10-25).

### Domain and HTTPS (15) — verified, one limitation

- Azure HTTPS: Let's Encrypt certificate for both names, HTTP-to-HTTPS 301, `openssl` output, renewal dry run: [how-this-site-is-secured.md](how-this-site-is-secured.md).
- Railway cutover DNS and HTTPS checks, before and after: [railway-migration.md §3–4](evidence/railway-migration.md#3-before-cutover).
- `http://www` and `https://www` both return 301 to `https://adamriddick.me/`: [railway-migration.md §6](evidence/railway-migration.md#6-www-redirect).
- **Limitation:** the root record is Proxied while Railway's certificate is blocked by a Let's Encrypt rate limit: [railway-migration.md §5](evidence/railway-migration.md#5-investigated-failure-tls-certificate-after-switching-to-dns-only).

### Railway / PostgreSQL migration (25) — verified

- Plan and dependency inventory written before the change: see section 1.
- PostgreSQL compatibility changes and transfer tool: commit `0e1c226`, [`scripts/transfer_database.py`](../scripts/transfer_database.py), [`tests/test_database_transfer.py`](../tests/test_database_transfer.py), [`migrations/`](../migrations/versions/0001_initial_schema.py).
- Railway setup, real data change, cutover, rollback: [railway-migration.md](evidence/railway-migration.md).
- Who manages what on Azure vs Railway: [README](../README.md#who-manages-what-azure-vs-railway).
- Source and target comparison: all eight table counts match, every row ID and name matches the Azure source (October 25 read-only query), and Railway holds the transferred Azure rows, not seed data; the original transfer run was not recorded: [railway-migration.md §2](evidence/railway-migration.md#2-current-data-comparison).

### Verified website update (5) — verified

- Commit `ae000c0`, reviewed and tested locally, deployed by Railway from GitHub ("Deployment successful"), serving the live domain: [railway-migration.md §7](evidence/railway-migration.md#7-verified-website-update).
- Second example: commit `0c5c65f` (GA4 ID fix), deployed and verified in GA4 Realtime.
- Third example: the placeholder-label change, deployed by Railway and checked on the live site: [railway-migration.md §7](evidence/railway-migration.md#7-verified-website-update).
- Recovery for code and data: [README > Rollback](../README.md#rollback).

### Zoho email (15) — verified; before-MX test not performed

- Received, replied, and new outgoing message table; SPF, DKIM, DMARC all PASS: [ex06.md](evidence/ex06.md).
- Screenshots: [Test 04 authentication](evidence/screenshots/Original%20Script.png), [Test 04 in Gmail](evidence/screenshots/Excercise%206%20evidence.png), [MX records](evidence/screenshots/MX%20record.png), [Reply 1](evidence/screenshots/Reply%201.png), [Reply 2](evidence/screenshots/Reply%202.png).
- Managed vs self-hosted email decision: [README](../README.md#decision-2-managed-email-with-zoho-instead-of-my-own-mail-server).
- **Not performed:** the before-MX test; the first inbound test came after MX was published. Recorded honestly in [ex06.md](evidence/ex06.md#before-mx-was-published).

### Google Analytics 4 (10) — verified

- Investigation of the wrong Measurement ID, fix in `0c5c65f`, and Realtime verification of `page_view` and outbound `click` with `link_url`: [ex06.md > GA4](evidence/ex06.md#google-analytics-4).
- Screenshots: [Realtime events](evidence/screenshots/ga4-realtime-events.png), [Realtime click link_url](evidence/screenshots/ga4-realtime-click-link.png), [click sent with the wrong ID](evidence/screenshots/ga4-click-details.png).
- Consent implementation: [`static/analytics-consent.js`](../static/analytics-consent.js), [Privacy page](https://adamriddick.me/privacy).

### Engineering record (20)

- Failures: [README > Investigated failures](../README.md#investigated-failures) (application: [ex03](evidence/ex03.md); DNS/TLS: [ex05 simulation](evidence/ex05.md) and the real cutover TLS failure).
- Decisions: [README > Decisions](../README.md#decisions).
- Reflection: [README > Reflection](../README.md#reflection).
- Costs, expiration dates, cleanup: [README > Costs](../README.md#costs-expiration-dates-and-cleanup).
- Remaining limitations: [README > Remaining limitations](../README.md#remaining-limitations).
