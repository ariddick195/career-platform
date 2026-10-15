import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import func, insert, select

import db_schema
import main
from database import DatabaseConfigurationError, create_engine_for_url
from seed_data import SeedConfigurationError, seed_development_data


class SeedDataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="career-platform-seed-")
        self.addCleanup(self.directory.cleanup)
        self.engine = create_engine_for_url(
            f"sqlite:///{(Path(self.directory.name) / 'seed.db').as_posix()}"
        )
        self.addCleanup(self.engine.dispose)
        db_schema.metadata.create_all(self.engine)

    def count(self, table):
        with self.engine.connect() as connection:
            return connection.scalar(select(func.count()).select_from(table))

    def test_development_seed_is_idempotent_and_only_fills_an_empty_profile(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
            seed_development_data(self.engine)
            seed_development_data(self.engine)

        self.assertEqual(self.count(db_schema.person), 1)
        self.assertEqual(self.count(db_schema.education), 1)
        self.assertEqual(self.count(db_schema.experience), 1)
        self.assertEqual(self.count(db_schema.project), 1)
        self.assertEqual(self.count(db_schema.skill), 4)
        self.assertEqual(self.count(db_schema.certification), 3)
        self.assertEqual(self.count(db_schema.volunteer_experience), 0)
        self.assertEqual(self.count(db_schema.link), 1)

    def test_seed_refuses_production_without_inserting_rows(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
            with self.assertRaises(SeedConfigurationError):
                seed_development_data(self.engine)

        self.assertEqual(self.count(db_schema.person), 0)

    def test_seed_refuses_non_sqlite_engine_before_connecting(self):
        postgres_engine = create_engine_for_url(
            "postgresql+psycopg://user:password@localhost/career_platform_test_seed"
        )
        self.addCleanup(postgres_engine.dispose)

        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
            with self.assertRaises(SeedConfigurationError):
                seed_development_data(postgres_engine)

    def test_seed_leaves_a_populated_profile_unchanged(self):
        with self.engine.begin() as connection:
            connection.execute(insert(db_schema.person).values(id=42, full_name="Existing"))

        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
            seed_development_data(self.engine)

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.scalar(select(db_schema.person.c.full_name).where(db_schema.person.c.id == 42)),
                "Existing",
            )
        self.assertEqual(self.count(db_schema.education), 0)


class DatabaseLifespanTests(unittest.TestCase):
    def run_lifespan(self):
        async def run():
            async with main.app.router.lifespan_context(main.app):
                pass

        asyncio.run(run())

    def test_missing_production_database_url_fails_during_startup(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(DatabaseConfigurationError, "DATABASE_URL"):
                self.run_lifespan()

    def test_invalid_production_database_url_fails_during_startup(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "DATABASE_URL": "postgresql://user:secret@/missing-host",
            },
            clear=True,
        ):
            with self.assertRaises(DatabaseConfigurationError) as raised:
                self.run_lifespan()

        self.assertNotIn("secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
