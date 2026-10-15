# Railway and PostgreSQL Migration Design

## Purpose

Move the existing FastAPI career profile from its Azure VM and SQLite production database to the Railway web service and PostgreSQL service that already exist. Keep SQLite as the local development database. Preserve the verified production profile and all related records, prevent sample data from entering production, and keep Azure available as the rollback target through Railway and custom-domain verification.

This document is the migration specification. The named guide `migrate-to-railway.md` is not in the local checkout; this revision follows its conversation-supplied required sequence: prepare the Railway service and database connection, transfer and verify production data, deploy and verify the Railway domain, then complete the Railway custom-domain and Cloudflare DNS steps and verify DNS/HTTPS. It also follows the repository's staged Superpowers workflow. It does not authorize application changes, remote service changes, DNS changes, commits, or deployment.

## Current application and verified source data

- The application is FastAPI with Jinja templates and sync route handlers in `main.py`.
- Database access is direct `sqlite3`, currently initialized at module import. `DATA_DIR` defaults to the repository's `data` directory; local SQLite is `career-platform.db`.
- The current schema has eight tables: `person`, `education`, `experience`, `project`, `skill`, `certification`, `volunteer_experience`, and `link`. Child records carry `person_id`; the current SQLite schema does not declare foreign-key constraints.
- SQL uses SQLite `?` placeholders and SQLite-specific `executescript`; this must be replaced by portable database access and versioned schema migrations.
- Local seed records are inserted when `person` is empty. Production must never run this sample-data path.
- The authoritative live Azure database is `/var/lib/career-platform/career-platform.db`. Its verified backup is `/var/lib/career-platform/career-platform.db.backup-20261013`. The downloaded `data/career-platform-production-backup.db` has the same SHA-256 hash as that Azure backup, and the Azure backup passed SQLite's integrity check.
- Verified source counts are: person=1, education=1, experience=1, project=3, skill=4, certification=3, volunteer_experience=3, link=4.
- These facts establish a trusted rehearsal source. Before cutover, the live database must be frozen for writes and backed up again so the final transfer includes any changes made after the verified backup.

## Goals and acceptance criteria

### Database behavior

1. With local development configuration and no `DATABASE_URL`, the app uses SQLite under `DATA_DIR` and retains the existing developer seed behavior.
2. With production configuration, the app requires PostgreSQL through `DATABASE_URL`. Missing or malformed production database configuration fails startup clearly; it must not silently create or use an empty SQLite database.
3. The web app uses a shared database-access layer compatible with SQLite and PostgreSQL. Existing public and admin routes, field values, ordering, and CRUD behavior remain available.
4. Schema changes are represented by ordered, versioned migrations. Applying migrations to a new database creates the complete schema; applying them again is a no-op. Migration execution is explicit and repeatable, not an unversioned table-creation side effect at module import.
5. Production startup/deployment never inserts example profile content. A production database with no imported profile stays empty and reports a clear operational failure/state rather than being filled with sample content.
6. Profile child rows retain their original primary keys and `person_id` values. Referential checks confirm every child still points to the same profile record. Any foreign-key constraints added to PostgreSQL must be validated against the source before cutover.

### Data-transfer behavior

7. A one-time transfer utility imports all eight tables from a SQLite source into an already migrated PostgreSQL target in a single transaction, preserving IDs, nullable values, booleans, text, row contents, and relationships.
8. The import target may already have its Alembic-managed schema and migration-version table, but all application tables must contain zero rows before import. By default, the importer rejects any target with existing application rows; normal application startup cannot invoke the transfer. Any populated-target recovery procedure must be explicit and separately documented.
9. After the rehearsal import from `data/career-platform-production-backup.db`, counts match the verified source counts exactly. Content-level verification compares source and target rows in deterministic primary-key order, not counts alone.
10. PostgreSQL identity/sequence values are advanced beyond imported IDs so the next admin insert cannot collide with an imported key.
11. The cutover transfer uses a fresh backup from the live Azure database after admin writes are disabled. Its integrity check and SHA-256 are recorded and the downloaded transfer file is confirmed identical to the source backup before import.
12. `data/career-platform-production-backup.db` remains a local, Git-ignored reference artifact only. Do not add it to Git or modify it as part of the migration implementation.

### Railway networking and HTTP behavior

13. The Railway web process binds to `0.0.0.0` and the runtime-provided `PORT`, with a local fallback port for developer use.
14. The app correctly interprets Railway's trusted forwarded HTTPS scheme and original host for request URL construction and same-origin admin-write validation. Railway currently documents `X-Forwarded-Proto` and `X-Forwarded-Host` on public requests.
15. On the Railway preview URL and final custom domain over HTTPS, an authenticated same-origin admin form POST succeeds; missing, mismatched-scheme, and mismatched-host Origin requests are rejected before changing data.
16. The implementation trusts forwarded values only from the configured Railway ingress path. Arbitrary client-supplied forwarding headers must not allow an attacker to bypass origin validation.

### Cutover, verification, and rollback

17. Azure remains online and its database remains intact until Railway data, the Railway web service, HTTPS, and the custom domain have all been verified.
18. Azure admin writes are disabled during the final transfer and remain disabled while Railway becomes the sole writer. The Azure site can continue serving public reads during this period.
19. Before cutover completion, the Railway site must return the expected profile and record counts; public routes/static assets must work; admin authentication and same-origin writes must be verified over HTTPS; the custom domain must resolve to Railway and present valid HTTPS.
20. The rollback procedure freezes Railway admin writes, takes a PostgreSQL backup, transfers the complete current PostgreSQL dataset back to the Azure SQLite database, verifies all counts and relationships, and then directs the domain to Azure. If reverse transfer cannot be verified, keep writes frozen and retain both services/data for operator recovery rather than switching to stale Azure data.
21. The cutover runbook identifies the exact point after which Railway is the source of truth and names the operator-controlled actions required for Azure write freeze, Railway/DNS configuration, and domain verification.

## Proposed architecture

### Database-layer choice

Use SQLAlchemy Core for the shared synchronous database layer and Alembic for versioned migrations. Do not add ORM models or rewrite the route/template contract. Keep route handlers synchronous as they are today; use SQLAlchemy engines/connections, named bound parameters, and mapping-style rows behind a small set of existing-purpose helpers. The SQLite URL remains the default in local development and continues to honor `DATA_DIR`; Railway uses the PostgreSQL `DATABASE_URL` reference. Normalize Railway's Postgres URL only as required by the selected PostgreSQL driver. Production mode must fail closed if no PostgreSQL URL is configured.

This choice is weighed against a smaller custom DB-API adapter built around `sqlite3` and a PostgreSQL driver. The custom adapter would add fewer library dependencies and could be short initially, but it would also own placeholder translation, consistent row behavior, backend-specific DDL, migration version tracking and execution, and PostgreSQL identity-sequence handling. Those are exactly the cross-database behaviors this migration must make reliable. SQLAlchemy Core is a narrow query/connection layer rather than an ORM rewrite; Alembic supplies the required ordered migration history and repeatable upgrade state. For this app, that removes more bespoke compatibility and migration code than it adds while retaining SQLite and the current route behavior. Reconsider only if implementation inspection shows the current DB operations can be retained with a substantially smaller tested adapter without duplicating migration responsibilities.

Move database operations and schema responsibility out of `main.py`'s import-time initialization into focused database/configuration modules. Keep the existing template context shape, route paths, and data semantics. Make development seeding an explicit development-only action/path, separate from schema migrations and from production startup. The migration plan will pin exact modules, interfaces, and tests after this specification is approved.

Add a dedicated one-time data-transfer command that accepts a SQLite source and PostgreSQL destination from environment/configuration, validates the SQLite source, permits an Alembic-initialized schema but requires zero rows in every application table, and rejects populated targets by default. Import rows in dependency order in one PostgreSQL transaction, preserving primary and relationship IDs, advancing PostgreSQL sequences, and emitting per-table counts plus deterministic content digests. It must not print database credentials. A corresponding reverse transfer path or documented restore utility supports rollback from Railway to Azure SQLite.

Railway's start command must use the provided `PORT` and bind all interfaces. Request scheme/host handling must account for Railway's `X-Forwarded-Proto` and `X-Forwarded-Host` while limiting trust to Railway's ingress. Final behavior is verified with real requests through Railway; unit tests cover trusted and untrusted forwarding cases.

## Data migration and release sequence

The required Superpowers order is: user approves this written specification; then create and self-review the implementation plan; user reviews that plan and selects/approves the execution method; only then begin implementation. The implementation sequence is local implementation and rehearsal; manual Railway web-service/database setup; final Azure freeze and data transfer; Railway deployment and generated-domain verification; Railway custom-domain setup; Cloudflare DNS update; final DNS/HTTPS/application verification. Do not start implementation before both review gates are complete. Do not change Railway or Cloudflare during planning.

### Phase A: local implementation and rehearsal

1. Preserve the current application/database behavior as a baseline and add automated coverage for local SQLite operation, current read ordering, admin CRUD, and seed behavior.
2. Implement the shared database layer, explicit development seed guard, Alembic migrations, Railway port/proxy handling, and data-transfer commands.
3. Run the complete app test suite against SQLite. Run PostgreSQL integration tests against a disposable local/test database; do not point tests at production Railway Postgres.
4. Rehearse the migration using the verified downloaded backup. Verify SQLite integrity, counts, per-row content digests, and all `person_id` links before and after import. Verify repeat-run refusal against a populated PostgreSQL target and that a failed import rolls back fully.
5. Rehearse a reverse transfer into a disposable SQLite file and confirm row-for-row equality. Do not replace the live Azure database during rehearsal.

### Phase B: Railway staging

1. Inspect and record the existing Railway project's environment, web/Postgres service names, regions, build/start settings, healthcheck, current variables, generated domain, and custom-domain state without changing them.
2. In the Railway dashboard, confirm the existing web service is connected to the intended repository and branch; retain the existing service and Postgres service rather than creating replacements. Record the service region and current deployment settings.
3. After separately approved implementation, use an isolated Railway preview environment and database for staging if available. Keep custom DNS unchanged. Never point a staging deployment at the production Postgres database for tests that write data.
4. Configure the web service's start command to bind Uvicorn on `0.0.0.0` and `$PORT`; configure a healthcheck against the site's root route if supported. Set production mode and admin credentials as Railway variables/secrets. Add `DATABASE_URL` as a Railway reference to the existing Postgres service variable, not as a copied literal credential.
5. Apply Alembic migrations explicitly, confirm all application tables in the staging target have zero rows, import the verified backup, and verify exact data equality. The Alembic schema/version table may already contain rows. If Railway has no isolated staging database, do all destructive/failure-injection and write-route tests against disposable local PostgreSQL; reserve the existing Railway Postgres for the final cutover import.
6. Verify Railway deployment health, homepage, static assets, all profile sections, admin auth, same-origin POST behavior, rejected cross-origin writes, and no sample seed. Confirm logs do not expose secrets.

### Phase C: production cutover

1. Schedule an operator-approved cutover window and record the current Azure/domain configuration, root and `www` DNS record values/types/TTL/proxy status, Cloudflare SSL mode and redirect settings, and rollback steps.
2. Disable admin writes on Azure while leaving the Azure service and public reads online. Confirm no writer can modify the source during snapshot and transfer.
3. Create a fresh SQLite backup from `/var/lib/career-platform/career-platform.db`, run `PRAGMA integrity_check`, calculate SHA-256, and transfer it securely. Record the digest and confirm the received file has the same digest.
4. Confirm source counts and relationships. Apply current Alembic migrations to the production Railway database and confirm that every application table has zero rows before importing; the Alembic schema/version table may already contain rows.
5. Import the final snapshot in one transaction. Compare all table counts, deterministic row digests, IDs, and `person_id` relationships to the final source. Advance PostgreSQL sequences and run post-import checks.
6. Deploy/start Railway with production mode and Postgres only. Verify Railway's generated HTTPS domain first, including `/`, static resources, public profile content, and correct forwarded HTTPS/host behavior. Do not configure production admin credentials or write to the imported production dataset before custom-domain verification. Same-origin writes and off-origin rejection must already have passed on isolated staging. Keep Azure running with admin writes disabled.
7. In Railway service Settings → Public Networking, add the actual root custom domain and copy the exact CNAME target and TXT ownership-verification record shown by Railway. Add `www` as a second Railway custom domain only if it is intended to be served directly by Railway; if Cloudflare will redirect `www` to the root, keep that redirect in Cloudflare. Select the app's `$PORT` target when Railway asks for the custom-domain port. Do not substitute a target from an example, a prior exercise, or a stale DNS record.
8. In Cloudflare DNS, replace the old Azure A/AAAA records for the root and `www` hostnames with the Railway-provided CNAME records (root name `@`, and `www` as its own record or target as appropriate), and add each Railway TXT ownership-verification record exactly as displayed. For the root plus `www` setup, enable Cloudflare proxying for the web CNAMEs, enable Universal SSL, and set Cloudflare SSL/TLS mode to **Full** (not Full Strict), as required by Railway's Cloudflare domain workflow. Keep unrelated DNS records unchanged. Wait for Railway to verify both domains and for TLS to become active.
9. In Cloudflare Bulk Redirects, configure `https://www.adamriddick.me` to redirect to `https://adamriddick.me` with status 301, preserving query strings, subpaths, and path suffixes. If inspection shows the actual configured canonical hostname differs, use that verified hostname instead. Do not create a redirect that sends requests back to Azure.
10. Verify Railway shows the domain(s) verified, Cloudflare proxy detected, and the correct target port; verify DNS records/propagation, `https://adamriddick.me` certificate and HTTP-to-HTTPS behavior, `www` 301 to root, and homepage/static assets/profile content. Since Cloudflare proxying can return Cloudflare edge IPs in public DNS answers, verify the Cloudflare record target in its dashboard and the working endpoint/certificate externally rather than expecting public DNS to expose Railway's underlying address.
11. After domain and public-site checks pass, enable the configured Railway admin credentials and perform one same-origin HTTPS write using a temporary record. Remove that record immediately and confirm all imported production rows and counts are unchanged/restored; verify a cross-origin request is rejected without changing data. This is the final application check before declaring Railway the source of truth.
12. Only after all custom-domain, data, public-site, and admin checks pass, designate Railway as the production source of truth. Keep Azure running and its data intact through this verification milestone.

### Phase D: post-cutover rollback window

1. Monitor Railway availability, logs, database connectivity, public page correctness, and admin writes for the agreed observation period. The observation duration must be chosen before cutover.
2. To roll back, disable Railway admin writes and confirm no in-flight admin request remains. Take a logical Postgres backup and run the reverse transfer into the Azure SQLite database using a verified copy/atomic replacement procedure that preserves a recoverable pre-rollback Azure copy.
3. Verify Azure SQLite integrity, all eight counts, row digests, IDs, and relationships against the PostgreSQL snapshot. Do not point traffic to Azure if verification fails.
4. Restore Azure service configuration so it reads the verified restored database; only then revert Railway's domain attachment as needed and restore the recorded pre-cutover Cloudflare DNS records, proxy status, SSL mode, and redirects. Verify the domain resolves/routs to Azure and HTTPS/site operation succeeds before re-enabling Azure admin writes.
5. Keep Railway and its Postgres data intact until rollback is complete and the incident is understood. Re-enable admin writes on only the active production service.

## Test strategy

- **SQLite regression tests:** local startup without `DATABASE_URL`; development seed remains available; homepage, ordering, and admin CRUD match existing behavior.
- **Production configuration tests:** production mode without `DATABASE_URL` fails closed; production startup never invokes seeds; valid Postgres URL selects PostgreSQL.
- **Migration tests:** fresh SQLite/Postgres schema, ordered Alembic upgrade, idempotent current revision, and downgrade/recovery behavior where supported.
- **Transfer tests:** exact values/counts/IDs/relationships across all eight tables; identity sequence advancement; empty-destination guard; transaction rollback on an injected failure; reverse transfer equivalence.
- **Proxy/security tests:** trusted HTTPS forwarded scheme/host make same-origin writes pass; spoofed/untrusted headers do not; wrong scheme/host and missing Origin reject before database mutation.
- **Railway smoke checks:** bind on dynamic `PORT`; generated domain and custom domain return expected page; HTTPS is recognized by the app; admin flow works only with configured credentials.
- **Cutover checks:** record backup digest and SQLite integrity output; exact per-table counts and row digests match before and after transfer; domain/DNS and certificate checks pass; Azure remains available until all gates pass.

## Manual actions and unresolved inputs

- `migrate-to-railway.md` is not present in this checkout. This revision follows the guide's sequence and manual Railway/Cloudflare steps supplied in conversation. Confirm actual service names, DNS values, and exact dashboard prompts during implementation-plan review rather than copying example values.
- The Railway project/environment/service names, region, current build/start configuration, healthcheck, generated domain, variables, and custom-domain status are not available from repository inspection. They must be read from Railway before execution; this specification authorizes no settings changes.
- The DNS provider, current records/TTL, cutover window, observation duration, and operator(s) responsible for custom-domain/DNS changes remain to be identified.
- A fresh final Azure backup must be created at cutover; the verified October 13 backup is a trustworthy rehearsal source but may not include later edits.
- Railway database backup/PITR policy and external logical-dump storage/retention must be selected before production use.
- The exact Railway forwarded-header trust boundary and whether the edge preserves `Host` in addition to providing `X-Forwarded-Host` must be verified in a Railway preview deployment before accepting admin POSTs.
- The repo does not contain Railway deployment configuration. Whether the existing web service builds from Nixpacks or Docker and whether it supports a separate pre-deploy migration command must be inspected before writing implementation-specific commands.
- Railway's current [domain guide](https://docs.railway.com/networking/domains/working-with-domains) requires both the dashboard-provided CNAME and TXT records for verification; for its root-plus-`www` Cloudflare flow it documents proxied CNAMEs, Universal SSL, Full SSL/TLS mode, and a Cloudflare Bulk Redirect from `www` to the root. Confirm those current prompts and account features during execution; do not copy sample CNAME targets.

## Constraints and exclusions

- Keep local development on SQLite.
- Preserve all verified Azure production data, IDs, and relationships.
- Never seed sample records into production.
- Use versioned schema migrations.
- Handle Railway's runtime `PORT` and trusted forwarded protocol/host headers.
- Keep Azure running and its production data intact through Railway and custom-domain verification.
- No application files, dependencies, Railway settings, DNS records, remote services, or production data are changed by this specification.
- No commit or push is part of the planning deliverable.
- Retirement of Azure, deletion of any database/backup, UI/product changes, and schema expansion unrelated to this migration are out of scope.
