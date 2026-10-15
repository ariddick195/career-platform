# Railway and PostgreSQL Migration Runbook

This runbook records the manual sequence for a reviewed migration. It does not authorize changes to Railway, Cloudflare, DNS, Azure, or production databases. Use the values shown in the Railway and Cloudflare dashboards at execution time; this document intentionally contains no credentials or sample DNS targets.

## Operating rules

- Keep local development on SQLite. Use Alembic for schema changes and the explicit development seed command only on an empty local SQLite database.
- Never seed production. Production application startup does not migrate or seed.
- Preserve all profile rows, IDs, nullable values, and `person_id` relationships across all eight application tables.
- Keep Azure online and preserve its database until Railway data, application, HTTPS, and the root custom domain are fully verified.
- Keep Railway admin writes disabled until the public site and domain pass verification and the exact-origin security tests pass. Forwarded request headers do not authorize writes; production writes require the explicit `ADMIN_ALLOWED_ORIGINS` allowlist. Without a valid allowlist, write requests return `503`.
- Do not put secrets, database URLs, or downloaded database files in Git, command history, logs, or this runbook.

## Preflight and staging

Before making changes, record the Railway project and environment, existing web and PostgreSQL service names, region, repository and branch, build method, start command, health check, generated domain, and current custom domains. Record variable names only; do not copy secret values into notes. Preserve the existing services and PostgreSQL instance.

Confirm whether the project has an isolated preview environment and disposable database. Run migration and transfer integration tests against a disposable PostgreSQL database before staging verification. The test guard requires a loopback host and a database name beginning `career_platform_test_`; never use Railway or production credentials for this test. If Railway has no isolated staging database, keep destructive and failure-injection tests local and reserve Railway PostgreSQL for the final import.

Configure only the existing Railway web service after the implementation is reviewed:

- Set `APP_ENV=production`.
- Add `DATABASE_URL` as a Railway variable reference to the existing PostgreSQL service. Do not copy its credential value into application configuration.
- For an isolated staging environment only, add staging-specific `ADMIN_USERNAME` and `ADMIN_PASSWORD` as Railway secrets to verify staging admin authentication. Do not configure production admin credentials at this stage. Production writes remain disabled until the domain checks and security tests pass and `ADMIN_ALLOWED_ORIGINS` contains the exact verified HTTPS origin or origins.
- Use `uvicorn main:app --host 0.0.0.0 --port $PORT` as the start command.
- Apply schema migrations explicitly with `alembic upgrade head` through the Railway-supported one-off or pre-deploy mechanism confirmed during preflight. Verify the migration revision before importing data.
- Do not configure Cloudflare proxying, SSL/TLS settings, or DNS during staging.

Verify the generated Railway HTTPS domain first: homepage, static stylesheet, all profile sections and counts, admin authentication, allowlisted same-origin write behavior in the isolated environment, rejection of missing and cross-origin `Origin` values, and absence of sample data. Send spoofed `X-Forwarded-Proto`, `X-Forwarded-Host`, and `Forwarded` headers during the security check; they must not bypass the origin allowlist. Keep production writes disabled if the trust boundary has not been established and the safe alternative has not passed its security tests.

## Rehearsal data transfer

The downloaded `data/career-platform-production-backup.db` is a local, Git-ignored reference artifact for rehearsal only. Do not add it to Git or modify it. Its SHA-256 was verified against `/var/lib/career-platform/career-platform.db.backup-20261013`, and SQLite integrity checking passed on Azure. That verified backup and local copy are for rehearsal; neither replaces a fresh cutover snapshot. The previously verified source counts are:

| Table | Rows |
|---|---:|
| `person` | 1 |
| `education` | 1 |
| `experience` | 1 |
| `project` | 3 |
| `skill` | 4 |
| `certification` | 3 |
| `volunteer_experience` | 3 |
| `link` | 4 |

For rehearsal, import that artifact only into a disposable target. For production, take a fresh snapshot from the live Azure database after freezing Azure admin writes; the rehearsal artifact is not the final snapshot.

1. Freeze Azure admin writes for the transfer window while leaving Azure public reads online. Confirm no other writer can change the source.
2. Create a fresh SQLite backup from `/var/lib/career-platform/career-platform.db`. Run `PRAGMA integrity_check`, record the eight table counts, and calculate SHA-256. Transfer the file securely and compare its digest with the source. Keep the database file out of the repository.
3. Confirm that Railway PostgreSQL has the Alembic schema at the expected revision. Every application table must have zero rows before import; an Alembic version row is allowed. The importer refuses any existing application rows by default.
4. Prefer a private Railway SSH tunnel: run `railway connect <postgres-service> --tunnel-only` in one terminal and keep it open. In a second terminal, provide the local tunnel `DATABASE_URL` only through a secure, temporary process environment. Do not type a credential-bearing URL into a command, shell history, log, or repository.
5. Run the transfer utility with an explicit direction and source path:

   ```bash
   python -m scripts.transfer_database --direction sqlite-to-postgres --sqlite-path <verified-snapshot-path>
   ```

   Supply `DATABASE_URL` to that process from the active local tunnel. The command prints counts and deterministic digests, not connection credentials. A failed import is transactional and must leave no partial application rows.
6. Compare all eight table counts and digests. Verify IDs, nullable values, Boolean values, and each `person_id` relationship. Confirm the PostgreSQL sequences are advanced so subsequent inserts cannot collide with imported IDs. Do not begin application writes during verification.

## Root-domain cutover

Record the current root and `www` DNS records, TTLs, proxy status, SSL/TLS mode, and redirect settings before cutover. Keep the values in the operator's secure change record, not in Git.

1. Keep the Railway-generated HTTPS domain available and verified before starting the custom-domain step. Keep Azure online and admin writes frozen.
2. In Railway Public Networking, add the root domain only, consistent with the trial allowance of one custom domain. Copy Railway's actual root CNAME target and actual verification TXT record from the dashboard into the secure change record. Do not substitute examples or targets from old notes.
3. Before changing DNS, verify in the Cloudflare account the actual record-type procedure for applying Railway's target to the root `@` record; do not assume a record type or representation. Follow the verified account procedure consistent with the approved migration plan, keep the root record DNS-only (grey cloud), and add Railway's actual verification TXT record. Leave every other DNS record unchanged, including `www`, AAAA, mail, and unrelated records.
4. Do not enable Cloudflare proxying. Do not change Universal SSL or Full SSL/TLS settings. Only revisit these settings if a separately verified issue requires a change and the owner approves it.
5. Do not add `www` unless the current Railway account allowance is verified to permit an additional custom domain and the owner chooses to use it. Until then, leave its DNS and redirect configuration unchanged.
6. Wait for Railway domain verification and certificate issuance. Verify root DNS, Railway's certificate, HTTPS, and the public site including static assets. Verify all imported profile sections and the source counts. If any check fails, leave Azure active and restore the recorded root DNS value before making another attempt.
7. Only after the root domain, HTTPS, static assets, and data checks pass, configure the production `ADMIN_USERNAME` and `ADMIN_PASSWORD` secrets and `ADMIN_ALLOWED_ORIGINS` with the exact verified HTTPS origin. Verify an authenticated same-origin write using a temporary record, then delete that record immediately. Verify the imported production data and counts remain intact, and verify a rejected cross-origin write causes no unintended mutation. Keep production writes disabled if these checks fail. Keep Azure online until all final verification is complete.

## Rollback

If Railway fails verification or during the agreed observation period:

1. Disable Railway admin writes and confirm no in-flight write remains. Keep Azure online and do not re-enable Azure writes yet.
2. Take a PostgreSQL backup. Create a **new** SQLite destination and apply Alembic migrations to it before reverse transfer. Export the complete current data to that file using the reverse transfer direction; the utility refuses to overwrite an existing destination. Verify SQLite integrity, all eight counts and digests, IDs, and relationships. Preserve the pre-rollback Azure database as a separate recoverable copy.
3. If reverse export cannot be verified, keep writes frozen and retain both services and datasets for recovery. Do not route users to stale Azure data.
4. Only after the new SQLite copy is verified, stop the Azure app before installing it with a recoverable replacement procedure. Start Azure and verify its public site and data.
5. Restore the recorded root DNS state and any other operator-approved prior settings. Do not alter unrelated DNS records. Verify HTTPS and public behavior on Azure before re-enabling Azure admin writes.
6. Keep Railway and its PostgreSQL data intact until rollback is complete and the incident is understood. Enable writes on only the active production service.

## Operator record to complete at execution time

Record actual service names, migration revision, source snapshot path and digest, table counts and digests, import result, Railway-generated domain checks, the exact dashboard-provided root CNAME target and verification TXT record, prior and new root DNS values, certificate status, security test results, and rollback owner. Keep secrets and raw connection strings out of this record.
