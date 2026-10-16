# Railway and PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the career profile's production data and app from Azure SQLite to the existing Railway web/PostgreSQL services while keeping local development on SQLite and preserving a verified rollback path.

**Architecture:** Add a small synchronous SQLAlchemy Core database layer and Alembic migrations, retaining the existing FastAPI routes and template data shape. Use an explicit, transactional transfer utility for SQLite/PostgreSQL data movement; configure Railway's dynamic port and trusted forwarded origin handling; stage and verify before the owner performs the manual domain cutover.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy Core, Alembic, psycopg 3, SQLite, PostgreSQL, Railway, Cloudflare, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-13-railway-postgresql-migration-design.md`

## Global Constraints

- Keep local development on SQLite.
- Preserve all verified Azure production data, IDs, and relationships.
- Never seed sample records into production.
- Use versioned schema migrations.
- Handle Railway's runtime `PORT` and trusted forwarded protocol/host headers.
- Keep Azure running and its production data intact through Railway and custom-domain verification.
- The import target may already have its Alembic-managed schema and migration-version table, but all application tables must contain zero rows before import.
- By default, the importer rejects any target with existing application rows; imports remain transactional.
- `data/career-platform-production-backup.db` remains a local, Git-ignored reference artifact. Do not add it to Git or modify it.
- Do not change Railway, Cloudflare, DNS, or other remote services as part of local implementation. The owner performs those manual actions only after separately approving the operational cutover.
- No production transfer uses the rehearsal backup as the final snapshot; create and verify a fresh Azure backup during the cutover window.

## Review Focus

- Production environment with missing or SQLite `DATABASE_URL`: startup must fail closed and never seed sample content. Test in Task 1 and Task 2.
- Alembic-initialized PostgreSQL database whose application tables are empty: importer must accept it; any populated application table must make default import fail before writing. Test in Task 3.
- Import failure after some rows have been read: PostgreSQL transaction must roll back all inserted application rows. Test in Task 3.
- Imported IDs and `person_id` links: all eight tables must match source rows and counts, and subsequent inserts must not collide with imported IDs. Test in Task 3.
- Spoofed or incomplete forwarded headers and HTTPS Origin checks: untrusted proxy values must not authorize a cross-origin write; trusted Railway HTTPS requests must preserve the existing same-origin behavior. Test in Task 4 and verify in Railway staging.
- Domain scope: configure the root domain only under the guide's one-custom-domain trial limit. Add `www` only after verifying the current account allowance supports an additional custom domain.
- Proxy security: production admin writes remain disabled unless Railway's forwarded-header trust boundary is established independently of request headers, or a safe alternative is implemented and its security tests pass.

---

### Task 1: Add database configuration and versioned schema

**Files:**
- Create: `database.py`
- Create: `db_schema.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/0001_initial_schema.py`
- Modify: `pyproject.toml`, `requirements.txt`, `uv.lock`
- Test: `tests/test_database_configuration.py`, `tests/test_migrations.py`

**Interfaces:**
- Produces `database_url_from_env(environ: Mapping[str, str] | None = None) -> URL`; the default SQLite URL is rooted at the repository's `data/career-platform.db`, independent of the process working directory.
- Produces `create_engine_for_url(url: URL | str) -> Engine` and `get_engine() -> Engine`.
- App startup validates runtime settings and constructs the engine without applying migrations or opening a database write transaction.
- `db_schema.py` exports `metadata` and SQLAlchemy `Table` definitions for the eight existing application tables.
- Alembic's `target_metadata` is `db_schema.metadata`.

- [ ] **Step 1: Write database configuration tests**

Test `database_url_from_env` for these cases: development without `DATABASE_URL` returns SQLite under `DATA_DIR`; production with a PostgreSQL URL returns a psycopg SQLAlchemy URL; production without a URL and production with a SQLite URL raise a clear configuration error. Assert errors do not include a supplied password.

- [ ] **Step 2: Run the configuration tests and confirm they fail**

Run: `uv run python -m unittest discover -s tests -p test_database_configuration.py -v`

Expected: the tests fail because `database_url_from_env` and the database configuration module do not exist.

- [ ] **Step 3: Add the database dependencies and configuration layer**

Add `SQLAlchemy>=2.0,<3`, `alembic>=1.13,<2`, and `psycopg[binary]>=3.2,<4` to both dependency manifests and regenerate `uv.lock` without upgrading unrelated dependencies. Implement the functions above. Use `APP_ENV=development` as the local default; when no URL is supplied, derive the SQLite path from repository-root `data/career-platform.db`, honoring `DATA_DIR`. Require a PostgreSQL URL when `APP_ENV=production`.

- [ ] **Step 4: Run configuration tests and confirm they pass**

Run: `uv run python -m unittest discover -s tests -p test_database_configuration.py -v`

Expected: all URL-selection and fail-closed tests pass.

- [ ] **Step 5: Write schema migration tests**

Add tests that apply Alembic to a new temporary SQLite file, assert all eight tables and expected columns exist, then apply `upgrade head` again, downgrade to `base`, and upgrade again. Assert the current revision after each transition. Add a PostgreSQL integration variant gated on a disposable `TEST_DATABASE_URL`; before connecting, require a loopback host and a database name beginning `career_platform_test_`, and reject Railway domains or any URL that fails either guard. Never use production credentials.

- [ ] **Step 6: Implement the shared schema and initial migration**

Define each current table and column in `db_schema.py`, retaining integer primary keys, existing text fields, nullable behavior, and `person_id` values. Represent `is_current` as a Boolean compatible with SQLite's integer storage. Do not add unrelated fields or constraints. Add an Alembic revision that creates and drops this schema, and configure the migration environment to use `database_url_from_env`.

- [ ] **Step 7: Run migration tests**

Run: `uv run python -m unittest discover -s tests -p test_migrations.py -v`

Expected: fresh SQLite migration and repeat-upgrade pass; PostgreSQL coverage passes when a disposable test URL is supplied and otherwise skips with a clear reason.

- [ ] **Step 8: Commit the database foundation**

```bash
git add database.py db_schema.py alembic.ini migrations pyproject.toml requirements.txt uv.lock tests/test_database_configuration.py tests/test_migrations.py
git commit -m "feat: add portable database configuration and migrations"
```

### Task 2: Move app queries to SQLAlchemy and isolate development seeding

**Files:**
- Modify: `main.py`
- Create: `seed_data.py`
- Create: `scripts/__init__.py`, `scripts/seed_dev.py`
- Modify: `tests/test_admin_security_and_home.py`
- Test: `tests/test_database_runtime.py`

**Interfaces:**
- Consumes `database.get_engine()` and `db_schema` tables from Task 1.
- `seed_data.seed_development_data(engine: Engine) -> None` inserts the current sample profile only when `APP_ENV=development`, the engine is SQLite, and `person` has no rows.
- `scripts.seed_dev.main() -> int` runs Alembic first only when explicitly invoked as documented, then runs the guarded development seed command.
- Existing `profile_data()` retains its dictionary keys and row ordering; public/admin route paths and form fields do not change.

- [ ] **Step 1: Add regression tests around isolated SQLite databases**

Update the current test fixture to create a temporary SQLite engine, apply the initial migration, inject the engine into app/database access, and invoke the explicit development seed helper. Keep assertions for public profile rendering, row ordering, admin authentication, all existing POST routes, and same-origin checks. Add a fresh-process import test that sets a temporary `DATA_DIR`, imports `main`, and asserts no database file or sample rows were created. Add an app-lifespan test proving missing or malformed production database settings fail startup before the app serves a request.

- [ ] **Step 2: Run the focused app tests and confirm the import/startup assertion fails**

Run: `uv run python -m unittest discover -s tests -p test_admin_security_and_home.py -v`

Expected: the fresh-process import test fails against the current `initialize()` call at module import.

- [ ] **Step 3: Implement SQLAlchemy query access without changing route behavior**

Replace `sqlite3` connections, `?` placeholders, `executescript`, and row conversion in `main.py` with SQLAlchemy Core connections, `text()` statements using named parameters, and mapping rows. Remove import-time schema creation. Keep the query ordering (`start_date DESC` for education/experience/volunteer; otherwise `id ASC`) and all route/form semantics unchanged.

- [ ] **Step 4: Add the guarded, explicit local seed command**

Move the existing seed values into `seed_data.py`. The seed function must reject production mode and non-SQLite engines, return without changes when a profile already exists, and insert all sample rows in one transaction only when the local profile is empty. Keep it out of app startup and migrations.

- [ ] **Step 5: Run focused app tests and confirm they pass**

Run: `uv run python -m unittest discover -s tests -p test_admin_security_and_home.py -v`

Expected: all existing admin/home behavior passes; importing `main` has no database side effect; development seed is explicit and idempotent; production seed attempts are rejected.

- [ ] **Step 6: Commit the app database refactor**

```bash
git add main.py seed_data.py scripts tests/test_admin_security_and_home.py tests/test_database_runtime.py
git commit -m "refactor: use shared database layer and explicit dev seed"
```

### Task 3: Build transactional SQLite/PostgreSQL transfer and verification

**Files:**
- Create: `scripts/transfer_database.py`
- Create: `tests/test_database_transfer.py`
- Modify: `db_schema.py` only if a source-compatible type mapping is required

**Interfaces:**
- `transfer_sqlite_to_postgres(sqlite_path: Path, target_engine: Engine) -> TransferReport`.
- `transfer_postgres_to_sqlite(source_engine: Engine, sqlite_path: Path) -> TransferReport`.
- `insert_table_rows(connection: Connection, table: Table, rows: Sequence[Mapping[str, object]]) -> None` is the single row-insertion seam used by the transfer and its injected-failure rollback test.
- `TransferReport` is a frozen dataclass with `table_counts: dict[str, int]` and `table_digests: dict[str, str]`; it never contains connection URLs or credentials.
- CLI uses `--direction sqlite-to-postgres|postgres-to-sqlite` and `--sqlite-path PATH`; PostgreSQL connection details come from the process `DATABASE_URL` environment only.

- [ ] **Step 1: Write transfer safety and fidelity tests**

Use a fixture database with exact source counts `person=1, education=1, experience=1, project=3, skill=4, certification=3, volunteer_experience=3, link=4`. Test imports into (a) a migrated schema with zero application rows plus an Alembic version row, (b) a target with one application row, and (c) a target where an injected insert error occurs. Assert exact values, IDs, `person_id` links, digests, and sequence advancement after success; assert populated-target refusal and complete rollback after failure. Test reverse transfer into a new SQLite file.

- [ ] **Step 2: Run transfer tests and confirm they fail**

Run: `uv run python -m unittest discover -s tests -p test_database_transfer.py -v`

Expected: transfer functions and report type do not exist; no target rows are inserted.

- [ ] **Step 3: Implement source validation, empty-target guard, and forward transfer**

Before connecting/importing, require source SQLite `PRAGMA integrity_check` to return `ok`, require all destination application tables to exist, and require each application table to contain zero rows. Ignore the Alembic version table for this test. Reject a populated target before inserting anything. Read rows in primary-key order and insert all eight tables in dependency order inside one PostgreSQL transaction, preserving IDs, values, nullable fields, and `person_id` references.

- [ ] **Step 4: Implement stable reports and PostgreSQL sequence advancement**

Calculate a SHA-256 digest from canonical JSON serialization of each table's ordered rows; normalize `is_current` to a semantic Boolean so SQLite integer `0/1` compares with PostgreSQL `false/true`. After inserting explicit IDs, advance each PostgreSQL identity sequence beyond the table's maximum imported ID. Report counts/digests without printing `DATABASE_URL` or credentials.

- [ ] **Step 5: Implement reverse transfer and CLI direction handling**

Use the same fidelity checks to export PostgreSQL rows to a new SQLite target file. First apply the Alembic schema to a temporary sibling SQLite file, then import the rows there. Refuse to overwrite an existing file; validate the temporary file and atomically move it to the requested output only after transaction and validation succeed. Ensure the CLI requires an explicit direction and SQLite path.

- [ ] **Step 6: Run transfer tests and confirm they pass**

Run: `uv run python -m unittest discover -s tests -p test_database_transfer.py -v`

Expected: zero-row migrated target imports; target with any app rows rejects; failure leaves no partial app rows; reverse transfer matches the source digests; next generated IDs exceed imported IDs.

- [ ] **Step 7: Commit the transfer utility**

```bash
git add scripts/transfer_database.py tests/test_database_transfer.py db_schema.py
git commit -m "feat: add verified transactional database transfer"
```

### Task 4: Handle Railway port and trusted forwarded request origin

**Files:**
- Create: `forwarded_headers.py`
- Modify: `main.py`
- Create: `tests/test_forwarded_headers.py`
- Modify: `tests/test_admin_security_and_home.py`

**Interfaces:**
- `forwarded_headers.public_origin(scope: Scope, trusted_proxy: bool) -> tuple[str, str]` returns normalized `(scheme, host)` from the ASGI request scope; untrusted scopes use only the direct scheme/Host values. The boolean is set only by the verified ingress trust check, never from a request header.
- `ForwardedOriginMiddleware(app, trust_proxy: Callable[[Scope], bool])` updates ASGI `scheme` and `Host` only for trusted Railway ingress requests, so `request.url` and the admin Origin check both see the public HTTPS origin.
- `require_admin` continues rejecting missing/cross-origin write requests and compares the submitted `Origin` against the resolved public origin.
- Production Uvicorn listens on `0.0.0.0:$PORT`; local execution retains Uvicorn's default port when `PORT` is unset.

- [ ] **Step 1: Inspect Railway's documented ingress behavior without changing settings**

During implementation preparation, record whether Railway overwrites `X-Forwarded-Proto` and `X-Forwarded-Host`, what the application receives in `Host`, and an independently verifiable network or platform boundary that identifies Railway ingress. Forwarded headers alone are never proof of trust. Treat establishing this boundary as a hard security gate. If it cannot be established, do not trust those headers: require a safe alternative (such as a platform-supported trusted-proxy mechanism or origin validation that remains secure without forwarded values), test it against spoofed headers, and keep production admin writes disabled until those security tests pass. Do not add a public database proxy or change domain/service configuration for this inspection.

- [ ] **Step 2: Write trusted/untrusted forwarded-origin tests**

Test an HTTPS Railway-style scope with forwarded host/scheme; it resolves to the public HTTPS origin and accepts a matching admin Origin. Test an untrusted peer with forged forwarding headers; they are ignored and cannot make a mismatched Origin pass. Test absent Origin, wrong scheme, and wrong host; writes return 403 and do not mutate the profile.

- [ ] **Step 3: Run forwarded-origin tests and confirm they fail**

Run: `uv run python -m unittest discover -s tests -p test_forwarded_headers.py -v`

Expected: the current request URL handling does not account for Railway's public forwarded host/scheme.

- [ ] **Step 4: Implement trusted public-origin resolution**

Implement `ForwardedOriginMiddleware` and `public_origin` using only the independently verified Railway ingress trust boundary from Step 1. Resolve `X-Forwarded-Proto` and `X-Forwarded-Host` only when that boundary is established, and update ASGI `scheme`/`Host`; never infer trust from header contents. If the boundary is unavailable, implement the safe alternative selected in Step 1 and prove forged/incomplete headers cannot authorize writes. Keep direct local request handling unchanged. Production admin writes stay disabled until the selected design passes its security tests.

- [ ] **Step 5: Set the Railway start command and run the HTTP tests**

Use `uvicorn main:app --host 0.0.0.0 --port $PORT` for Railway. Retain the local command that uses Uvicorn's default port when `PORT` is absent. Run:

`uv run python -m unittest discover -s tests -p test_forwarded_headers.py -v`

Expected: forwarded-origin and spoofing tests pass; existing same-origin and cross-origin admin tests still pass.

- [ ] **Step 6: Commit the port/proxy handling**

```bash
git add forwarded_headers.py main.py tests/test_forwarded_headers.py tests/test_admin_security_and_home.py
git commit -m "fix: validate admin origins behind Railway proxy"
```

### Task 5: Document local setup, Railway configuration, and operator runbook

**Files:**
- Modify: `README.md`, `.env.example`
- Create: `docs/railway-migration-runbook.md`

**Interfaces:**
- README local instructions use SQLite, `alembic upgrade head`, and the explicit development seed command.
- Railway runbook records exact operator actions and places for actual Railway-provided values; it contains no credentials or invented CNAME/TXT targets.

- [ ] **Step 1: Draft runbook acceptance checklist**

Include Railway inspection, existing service preservation, production variables (`APP_ENV=production`, `DATABASE_URL` reference, admin secrets), `$PORT` start command, and explicit migration command. Document `railway connect <postgres-service> --tunnel-only` as the preferred external connection path for transfer, so Postgres need not be given public TCP access. Keep the tunnel open in one terminal, set the importer process's `DATABASE_URL` from its local tunnel connection details in a second terminal, and keep those details out of shell history, logs, and the repository.

- [ ] **Step 2: Document local SQLite workflow and configuration**

Update `.env.example` with development mode and local `DATA_DIR` defaults, blank admin placeholders, and no live credentials. Update README local steps to create/activate the environment, apply Alembic migrations, run the explicit development seed, and start Uvicorn. Preserve the existing Azure operations notes until the owner retires Azure separately.

- [ ] **Step 3: Document data rehearsal, cutover, verification, and rollback**

The runbook must require using `data/career-platform-production-backup.db` only as a local Git-ignored rehearsal artifact. For production, freeze Azure admin writes; create a fresh backup from `/var/lib/career-platform/career-platform.db`; verify SQLite integrity, counts, and SHA-256; transfer it securely; run migrations; confirm all app tables have zero rows (Alembic version rows are allowed); import transactionally; verify counts/digests/IDs/relationships; and keep Azure online.

Document the Railway preview-domain checks, then manual Railway custom-domain setup for the root domain only, following Section 5 of `migrate-to-railway.md`: change the root `@` A record to the actual Railway-provided CNAME target with DNS-only (grey-cloud) status, and add Railway's actual verification TXT record. Leave every other DNS record unchanged. Do not configure `www` unless the account's current allowance is verified to permit an additional Railway custom domain and the owner elects to use it. Do not change Cloudflare Universal SSL or Full SSL/TLS settings unless a separately verified issue requires a change and the owner approves it. Do not remove or replace AAAA or other records unless a verified conflict requires it and the owner approves it. Document DNS propagation, Railway certificate and HTTPS checks, and data/site/admin acceptance. Record current DNS and SSL settings before cutover. Rollback freezes Railway writes, backs up PostgreSQL, transfers the latest dataset to a recoverable SQLite copy, verifies it, restores the recorded DNS settings, and only then re-enables Azure admin writes.

- [ ] **Step 4: Review documentation for secret and target leakage**

Search the README, `.env.example`, and runbook for passwords, live `DATABASE_URL` values, the actual Cloudflare token, and placeholder CNAME/TXT values that could be mistaken for the real target. Confirm only Railway dashboard-sourced values are used at execution time.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md .env.example docs/railway-migration-runbook.md
git commit -m "docs: add Railway database migration runbook"
```

### Task 6: Rehearse, stage, and perform the owner-directed cutover

**Files:**
- No application files; consume the artifacts from Tasks 1–5.
- Operator artifacts: verified transfer reports, Railway deployment/domain status, DNS/HTTPS verification output, and cutover/rollback log.

**Interfaces:**
- Forward import uses `scripts.transfer_database.transfer_sqlite_to_postgres` through the CLI and a local Railway SSH tunnel.
- Reverse transfer uses `scripts.transfer_database.transfer_postgres_to_sqlite` into a new SQLite file; it never overwrites the only Azure copy.
- Remote Railway/Cloudflare/DNS actions are performed by the owner after separate explicit authorization; this plan does not authorize remote changes by itself.

- [ ] **Step 1: Run the complete local test suite and database rehearsals**

Run: `uv run python -m unittest discover -s tests -v`

Expected: all SQLite tests pass. Run migration/transfer integration coverage against a disposable PostgreSQL database. Rehearse forward and reverse transfer using `data/career-platform-production-backup.db`; verify SQLite integrity, all eight counts, deterministic row digests, relationships, sequence advancement, empty-target refusal, and full rollback on injected failure. Do not change Azure or Railway production data.

- [ ] **Step 2: Inspect the existing Railway project read-only**

Record project/environment and web/Postgres service names, repository/branch, region, build method, deployment variables by key only, healthcheck, generated domain, custom domains, and whether an isolated preview environment/database is available. If no web service exists, record that fact; do not create one during this read-only step. Confirm the intended GitHub repository and branch and whether Railway is authorized to access that repository. Do not print secret values or change settings.

- [ ] **Step 3: Owner stages Railway and imports rehearsal data**

After separate authorization, preserve the existing PostgreSQL service. If the web service is absent, the owner creates one in the existing project/environment from the reviewed GitHub repository and branch; if Railway is not linked to GitHub, the owner links the account and grants the Railway GitHub App access to the selected repository. Confirm the service source and branch before proceeding. A linked branch may deploy on new pushes. Permit a deployment in Step 3 only to an isolated staging environment with separate authorization; otherwise hold deployment until Task 6 Step 5. Do not generate a root custom domain in this step.

Configure the web service with `APP_ENV=production`, a `DATABASE_URL` reference to the PostgreSQL service for its selected environment, and the `uvicorn main:app --host 0.0.0.0 --port $PORT` start command. Railway supplies `PORT`; do not set a fixed port. Confirm the healthcheck path and Railway-supported one-off or pre-deploy migration mechanism during preflight. If an isolated staging database exists, apply `alembic upgrade head` to that database only, verify the revision and zero application rows, then import the verified rehearsal backup through `railway connect <postgres-service> --tunnel-only`; staging-specific `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_ALLOWED_ORIGINS` may be used only in that isolated environment after its generated domain is verified. Validate staging data, profile, assets, admin authentication, same-origin/cross-origin behavior, and no sample seed. If no isolated staging database exists, do not migrate, import, or run the app against the existing Railway PostgreSQL service in Step 3; keep destructive tests local and reserve Railway PostgreSQL for the final import in Step 4. Keep production admin credentials and writes disabled until Task 6 Step 7.

- [ ] **Step 4: Owner conducts final Azure snapshot and Railway import**

During the approved window, disable Azure admin writes while leaving Azure public reads online. Create a fresh backup from `/var/lib/career-platform/career-platform.db`; record `PRAGMA integrity_check`, all eight counts, and SHA-256; securely download and compare the digest. Apply Alembic to the existing Railway Postgres; confirm all application tables have zero rows; import the final snapshot transactionally through the SSH tunnel; compare counts, digests, IDs, `person_id` relationships, and sequences. Keep Azure running and do not point DNS yet.

- [ ] **Step 5: Owner deploys and verifies Railway before custom-domain cutover**

Deploy the app to Railway with production mode, Postgres reference, `$PORT` binding, and no sample seed. Verify the generated HTTPS domain, root route, static files, all profile data/counts, forwarded scheme/host behavior, and logs. Keep production admin writes disabled until the domain and public-site checks pass and the Task 4 trust-boundary gate is established, or its safe alternative has passed spoofing/security tests. If that gate cannot be met, do not enable admin writes. If any data or runtime check fails, leave Azure active and repair Railway without changing DNS.

- [ ] **Step 6: Owner performs Railway and Cloudflare custom-domain steps**

In Railway Public Networking, add the verified root domain only and copy its actual CNAME target and verification TXT value. The guide's trial limit permits one custom domain; do not add `www` unless the account's current allowance is verified to permit another domain. In Cloudflare, change only the root `@` A record to the actual Railway-provided CNAME target and keep it DNS-only (grey-cloud); add Railway's actual verification TXT record. Leave every other DNS record unchanged. Do not change Universal SSL or Full SSL/TLS settings unless a separately verified issue requires a change and the owner approves it. Do not remove or replace AAAA or other records unless a verified conflict requires it and the owner approves it. Configure `www` only after verifying the extra Railway custom-domain allowance and recording the owner's choice. Wait for Railway verification and certificate issuance; verify root DNS, Railway's certificate, HTTPS, redirects, and public content. Preserve a record of all changes and prior values for rollback.

- [ ] **Step 7: Owner performs final admin check and declares cutover**

After the domain and public site checks pass, and only after the Task 4 security gate passes, configure the Railway admin secrets and verify an authenticated same-origin HTTPS write with a temporary record. Delete the temporary record immediately; verify existing imported data/counts remain intact and a cross-origin write is rejected without mutation. If the trust boundary is unavailable and the safe alternative has not passed its security tests, keep production admin writes disabled. Only then declare Railway the source of truth. Keep Azure online and its database intact through the full verification milestone.

- [ ] **Step 8: Keep rollback ready through the observation window**

Monitor Railway and keep the observation window selected before cutover. If rollback is needed, disable Railway writes and stop the Azure app service before replacing its database file. Take a Postgres backup, apply Alembic to a new SQLite destination, and reverse-transfer the complete current data into that file. Verify integrity/counts/digests/relationships, preserve the pre-rollback Azure database, and install the verified file using a recoverable atomic replacement. Restart Azure and verify its data and HTTPS before restoring the recorded DNS/proxy/SSL/redirect state and routing the domain back to Azure. Re-enable writes on one active production service only.

## Self-review coverage map

- Database configuration and missing/invalid production URL: Task 1 tests.
- Local SQLite schema, routes, seed behavior, and no import-time writes: Tasks 1–2 tests.
- Existing migration table with empty app tables, populated-target refusal, transactional failure, deterministic data fidelity, sequence advancement, and reverse copy: Task 3 tests.
- Railway proxy trust-boundary gate, forwarded scheme/host or safe alternative, same-origin HTTPS, wrong/missing Origin, and spoofed forwarding headers: Task 4 tests plus Task 6 staging verification; no production admin writes before successful security tests.
- Missing web service, conditional creation in the existing Railway project, reviewed GitHub repository/branch access, staging-only rehearsal, deployment hold, and required application variable names: Task 6 Steps 2–3 plus the runbook; preserve the existing PostgreSQL service and leave it unused until the final import when no isolated staging database exists.
- Root-only Railway custom domain under the trial allowance; change only the root `@` A record to Railway's actual CNAME target with DNS-only status and add the actual verification TXT record; preserve all other DNS and SSL settings unless a verified issue requires a change and the owner approves; verify Railway certificate/HTTPS; conditional `www` and rollback: Tasks 5–6 operator checklist.
- Production snapshot freshness, Azure write freeze, no seeding, production counts and IDs, and delayed source-of-truth switch: Task 6 cutover steps.

## Execution boundary

This plan is not approval to start implementation, modify Railway/Cloudflare/DNS, or deploy. The owner reviews this plan and chooses/approves an execution method first. Remote service and DNS actions still require separate explicit authorization and are owner-performed manual steps.
