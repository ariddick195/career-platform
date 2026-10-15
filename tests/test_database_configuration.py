import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.engine import URL

import database


class DatabaseConfigurationTests(unittest.TestCase):
    def test_development_defaults_to_repository_sqlite_path_independent_of_cwd(self):
        expected = Path(database.__file__).resolve().parent / "data" / "career-platform.db"

        with tempfile.TemporaryDirectory() as working_directory:
            with patch("pathlib.Path.cwd", return_value=Path(working_directory)):
                url = database.database_url_from_env({"APP_ENV": "development"})

        self.assertEqual(url.get_backend_name(), "sqlite")
        self.assertEqual(Path(url.database), expected)

    def test_development_honors_data_dir(self):
        with tempfile.TemporaryDirectory() as data_directory:
            url = database.database_url_from_env(
                {"APP_ENV": "development", "DATA_DIR": data_directory}
            )

        self.assertEqual(Path(url.database), Path(data_directory) / "career-platform.db")

    def test_production_normalizes_postgres_url_to_psycopg(self):
        url = database.database_url_from_env(
            {
                "APP_ENV": "production",
                "DATABASE_URL": "postgres://career:secret@localhost/career_platform",
            }
        )

        self.assertIsInstance(url, URL)
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.username, "career")
        self.assertEqual(url.password, "secret")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.database, "career_platform")

    def test_production_without_database_url_fails_closed(self):
        with self.assertRaisesRegex(database.DatabaseConfigurationError, "DATABASE_URL"):
            database.database_url_from_env({"APP_ENV": "production"})

    def test_production_rejects_sqlite_url_without_echoing_credentials(self):
        secret_url = "sqlite:///career-platform.db?password=top-secret"

        with self.assertRaises(database.DatabaseConfigurationError) as raised:
            database.database_url_from_env(
                {"APP_ENV": "production", "DATABASE_URL": secret_url}
            )

        self.assertNotIn("top-secret", str(raised.exception))

    def test_invalid_database_url_does_not_echo_password(self):
        with self.assertRaises(database.DatabaseConfigurationError) as raised:
            database.database_url_from_env(
                {
                    "APP_ENV": "production",
                    "DATABASE_URL": "postgresql://career:top-secret@",
                }
            )

        self.assertNotIn("top-secret", str(raised.exception))

    def test_create_engine_for_sqlite_does_not_create_database_until_connect(self):
        with tempfile.TemporaryDirectory() as data_directory:
            path = Path(data_directory) / "not-created.db"
            engine = database.create_engine_for_url(URL.create("sqlite", database=str(path)))
            try:
                self.assertFalse(path.exists())
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
