"""Shared SQLAlchemy database configuration for local and production use."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Mapping

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT_DIR / "data"


class DatabaseConfigurationError(ValueError):
    """Raised when runtime database settings are missing or unsupported."""


def database_url_from_env(
    environ: Mapping[str, str] | None = None,
) -> URL:
    """Return a validated SQLAlchemy URL without exposing URL credentials in errors."""

    settings = os.environ if environ is None else environ
    app_env = settings.get("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "production"}:
        raise DatabaseConfigurationError(
            "APP_ENV must be either 'development' or 'production'."
        )

    database_url = settings.get("DATABASE_URL", "").strip()
    if not database_url:
        if app_env == "production":
            raise DatabaseConfigurationError(
                "DATABASE_URL must point to PostgreSQL when APP_ENV=production."
            )
        data_directory = Path(settings.get("DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser()
        if not data_directory.is_absolute():
            data_directory = ROOT_DIR / data_directory
        return URL.create(
            "sqlite", database=str((data_directory / "career-platform.db").resolve())
        )

    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError):
        raise DatabaseConfigurationError("DATABASE_URL is not a valid database URL.") from None

    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    elif url.drivername == "postgresql+psycopg":
        pass
    elif url.get_backend_name() == "postgresql":
        raise DatabaseConfigurationError(
            "DATABASE_URL must use the psycopg PostgreSQL driver."
        )

    if url.get_backend_name() == "postgresql":
        if not url.host or not url.database:
            raise DatabaseConfigurationError(
                "DATABASE_URL must include a PostgreSQL host and database name."
            )
    elif app_env == "production":
        raise DatabaseConfigurationError(
            "DATABASE_URL must point to PostgreSQL when APP_ENV=production."
        )
    elif url.get_backend_name() != "sqlite":
        raise DatabaseConfigurationError("DATABASE_URL uses an unsupported database backend.")

    return url


def create_engine_for_url(url: URL | str) -> Engine:
    """Create an engine without connecting or creating a SQLite database file."""

    parsed_url = make_url(url) if isinstance(url, str) else url
    options: dict[str, object] = {"pool_pre_ping": True}
    if parsed_url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(parsed_url, **options)


_engine: Engine | None = None
_engine_lock = Lock()


def get_engine() -> Engine:
    """Return the process engine, validating configuration on first use."""

    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine_for_url(database_url_from_env())
    return _engine
