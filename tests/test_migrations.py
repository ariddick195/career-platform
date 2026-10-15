import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = ROOT / "alembic.ini"
APPLICATION_TABLES = {
    "person": {
        "id", "full_name", "location_city", "location_state", "location_country",
        "email", "phone", "career_goal", "summary", "profile_photo_url",
    },
    "education": {
        "id", "person_id", "institution_name", "city", "state", "country",
        "start_date", "end_date", "degree_name", "field_of_study", "relevant_coursework",
    },
    "experience": {
        "id", "person_id", "company_name", "city", "state", "country", "role_title",
        "start_date", "end_date", "is_current", "description", "achievements",
    },
    "project": {
        "id", "person_id", "title", "category", "course_name", "description",
        "technologies_used", "outcome", "project_url",
    },
    "skill": {"id", "person_id", "name", "category", "proficiency_level", "notes"},
    "certification": {
        "id", "person_id", "name", "issuing_organization", "completion_date", "credential_url",
    },
    "volunteer_experience": {
        "id", "person_id", "organization_name", "role_title", "start_date", "end_date",
        "location", "description",
    },
    "link": {"id", "person_id", "label", "url", "category"},
}


def make_alembic_config():
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def migration_revision(connection):
    row = connection.execute(
        "SELECT version_num FROM alembic_version"
    ).fetchone()
    return row[0] if row else None


class SQLiteMigrationTests(unittest.TestCase):
    def test_fresh_upgrade_repeat_downgrade_and_reupgrade(self):
        with tempfile.TemporaryDirectory() as data_directory:
            database_path = Path(data_directory) / "migration-test.db"
            database_url = f"sqlite:///{database_path.as_posix()}"
            config = make_alembic_config()

            with patch.dict(
                os.environ,
                {"APP_ENV": "development", "DATABASE_URL": database_url},
                clear=False,
            ):
                command.upgrade(config, "head")
                with closing(sqlite3.connect(database_path)) as connection:
                    self.assertEqual(migration_revision(connection), "0001_initial_schema")
                    self.assertEqual(
                        {
                            row[0]
                            for row in connection.execute(
                                "SELECT name FROM sqlite_master WHERE type='table'"
                            )
                        },
                        set(APPLICATION_TABLES) | {"alembic_version"},
                    )
                    for table, expected_columns in APPLICATION_TABLES.items():
                        actual_columns = {
                            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                        }
                        self.assertEqual(actual_columns, expected_columns, table)
                        row_count = connection.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0]
                        self.assertEqual(row_count, 0, table)

                command.upgrade(config, "head")
                with closing(sqlite3.connect(database_path)) as connection:
                    self.assertEqual(migration_revision(connection), "0001_initial_schema")

                command.downgrade(config, "base")
                with closing(sqlite3.connect(database_path)) as connection:
                    application_tables = {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }
                    self.assertFalse(application_tables & set(APPLICATION_TABLES))
                    self.assertEqual(migration_revision(connection), None)

                command.upgrade(config, "head")
                with closing(sqlite3.connect(database_path)) as connection:
                    self.assertEqual(migration_revision(connection), "0001_initial_schema")
                    for table, expected_columns in APPLICATION_TABLES.items():
                        actual_columns = {
                            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                        }
                        self.assertEqual(actual_columns, expected_columns, table)


class PostgreSQLMigrationTests(unittest.TestCase):
    def test_disposable_local_postgres_can_be_migrated(self):
        raw_database_url = os.environ.get("TEST_DATABASE_URL")
        if not raw_database_url:
            self.skipTest("set TEST_DATABASE_URL to a disposable local career_platform_test_* database")

        url = make_url(raw_database_url)
        host = (url.host or "").casefold()
        database_name = url.database or ""
        if host not in {"localhost", "127.0.0.1", "::1"}:
            self.fail("TEST_DATABASE_URL must use a loopback host")
        if "railway" in host or not database_name.startswith("career_platform_test_"):
            self.fail("TEST_DATABASE_URL must name a local career_platform_test_* database")

        config = make_alembic_config()
        with patch.dict(
            os.environ,
            {"APP_ENV": "development", "DATABASE_URL": raw_database_url},
            clear=False,
        ):
            command.upgrade(config, "head")
            command.upgrade(config, "head")
            command.downgrade(config, "base")
            command.upgrade(config, "head")


if __name__ == "__main__":
    unittest.main()
