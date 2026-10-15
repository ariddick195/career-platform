"""Apply local migrations and insert the development-only sample profile."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote

from alembic import command
from alembic.config import Config

from database import database_url_from_env, get_engine
from seed_data import SeedConfigurationError, seed_development_data


def main() -> int:
    if os.getenv("APP_ENV", "development").strip().lower() != "development":
        raise SeedConfigurationError("The development seed command requires APP_ENV=development.")
    url = database_url_from_env()
    if url.get_backend_name() != "sqlite":
        raise SeedConfigurationError("The development seed command requires a SQLite database.")
    if url.database and url.database != ":memory:":
        Path(unquote(url.database)).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")
    seed_development_data(get_engine())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
