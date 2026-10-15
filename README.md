# Adam Riddick Career Platform

A database-driven personal resume and career website for Adam Riddick.

## Features

- Relational SQLite data model for profile, education, experience, projects, skills, certifications, volunteer work, and links
- Public-facing resume and portfolio pages powered by database records
- Lightweight admin interface for managing content entries
- Placeholder support for any information not yet provided

## Getting started

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env, then set local admin credentials if desired.
# Windows PowerShell: Copy-Item .env.example .env
# Linux/macOS: cp .env.example .env
alembic upgrade head
python -m scripts.seed_dev
uvicorn main:app --reload --env-file .env
```

The app defaults to local SQLite at `data/career-platform.db`. Keep `APP_ENV=development` for local use. These commands create the schema with Alembic, then explicitly seed example profile content; application import and startup do not create or seed the database. The seed command only operates in development against SQLite and leaves an existing profile unchanged. Never run it in production. If you set a custom `DATA_DIR`, export it before running both migration and seed commands.

## Admin area

For local admin access, set non-empty `ADMIN_USERNAME` and `ADMIN_PASSWORD` values in `.env`. The blank values in `.env.example` are placeholders, not credentials. If either value is unset or blank, the public site remains available and admin access returns `503`. Open <http://127.0.0.1:8000>; admin access at `/admin` uses the browser's HTTP Basic authentication prompt.

See the [Railway migration runbook](docs/railway-migration-runbook.md) for deployment, transfer, verification, cutover, and rollback procedures.
