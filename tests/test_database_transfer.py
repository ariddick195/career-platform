import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from sqlalchemy import insert, select, text

import db_schema
from database import create_engine_for_url
from scripts.transfer_database import (
    TransferError,
    _advance_postgresql_sequences,
    transfer_postgres_to_sqlite,
    transfer_sqlite_to_postgres,
)


TABLES = (
    db_schema.person,
    db_schema.education,
    db_schema.experience,
    db_schema.project,
    db_schema.skill,
    db_schema.certification,
    db_schema.volunteer_experience,
    db_schema.link,
)
EXPECTED_COUNTS = {
    "person": 1,
    "education": 1,
    "experience": 1,
    "project": 3,
    "skill": 4,
    "certification": 3,
    "volunteer_experience": 3,
    "link": 4,
}


class DatabaseTransferTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="career-platform-transfer-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source_path = self.root / "source.db"
        self.source_engine = create_engine_for_url(
            f"sqlite:///{self.source_path.as_posix()}"
        )
        self.addCleanup(self.source_engine.dispose)
        self.target_engine = create_engine_for_url(
            f"sqlite:///{(self.root / 'target.db').as_posix()}"
        )
        self.addCleanup(self.target_engine.dispose)
        self.populate_source()
        self.prepare_target()

    def populate_source(self):
        db_schema.metadata.create_all(self.source_engine)
        with self.source_engine.begin() as connection:
            for table in TABLES:
                row_count = EXPECTED_COUNTS[table.name]
                rows = []
                for index in range(row_count):
                    row_id = 5 if table.name == "person" else 10 + index * 7
                    values = {"id": row_id}
                    for column in table.columns:
                        if column.name == "id":
                            continue
                        if column.name == "person_id":
                            values[column.name] = 5
                        elif column.name == "is_current":
                            values[column.name] = (None, False, True)[index % 3]
                        else:
                            values[column.name] = f"{table.name}-{index}-{column.name}"
                    rows.append(values)
                connection.execute(insert(table), rows)

    def prepare_target(self):
        db_schema.metadata.create_all(self.target_engine)
        with self.target_engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema')")
            )

    def table_rows(self, engine, table):
        with engine.connect() as connection:
            return [dict(row) for row in connection.execute(select(table).order_by(table.c.id)).mappings()]

    def counts(self, engine):
        with engine.connect() as connection:
            return {
                table.name: connection.scalar(text(f"SELECT COUNT(*) FROM {table.name}"))
                for table in TABLES
            }

    def test_forward_transfer_preserves_rows_ids_relationships_digests_and_next_ids(self):
        report = transfer_sqlite_to_postgres(self.source_path, self.target_engine)

        self.assertEqual(report.table_counts, EXPECTED_COUNTS)
        self.assertEqual(set(report.table_digests), set(EXPECTED_COUNTS))
        for table in TABLES:
            source_rows = self.table_rows(self.source_engine, table)
            target_rows = self.table_rows(self.target_engine, table)
            self.assertEqual(target_rows, source_rows, table.name)
            if table.name != "person":
                self.assertEqual({row["person_id"] for row in target_rows}, {5})
            max_id = max(row["id"] for row in source_rows)
            with self.target_engine.begin() as connection:
                values = {column.name: None for column in table.columns if column.name not in {"id", "person_id"}}
                if "person_id" in table.c:
                    values["person_id"] = 5
                connection.execute(insert(table).values(**values))
                next_id = connection.scalar(select(table.c.id).order_by(table.c.id.desc()).limit(1))
            self.assertGreater(next_id, max_id, table.name)

        with self.source_engine.connect() as connection:
            for table in TABLES:
                rows = [dict(row) for row in connection.execute(select(table).order_by(table.c.id)).mappings()]
                expected_digest = hashlib.sha256(
                    json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                ).hexdigest()
                self.assertEqual(report.table_digests[table.name], expected_digest)

    def test_postgresql_sequence_advancement_uses_each_nonempty_table_max_id(self):
        connection = Mock()
        rows_by_table = {
            table.name: [{"id": 2}, {"id": 17}] for table in TABLES
        }
        rows_by_table["person"] = [{"id": 5}, {"id": 42}]
        rows_by_table["experience"] = [{"id": 70}, {"id": 11}, {"id": 38}]
        rows_by_table["project"] = [{"id": 103}]

        _advance_postgresql_sequences(connection, rows_by_table)

        calls = {
            call.args[1]["table_name"]: call.args[1]["max_id"]
            for call in connection.execute.call_args_list
        }
        expected_maxima = {table.name: 17 for table in TABLES}
        expected_maxima.update({"person": 42, "experience": 70, "project": 103})
        self.assertEqual(calls, expected_maxima)
        self.assertEqual(connection.execute.call_count, len(TABLES))
        for call in connection.execute.call_args_list:
            self.assertIn("pg_get_serial_sequence", str(call.args[0]))
            self.assertTrue(call.args[0].text.endswith(", true)"))

    def test_postgresql_sequence_advancement_leaves_empty_table_sequences_alone(self):
        connection = Mock()
        _advance_postgresql_sequences(connection, {table.name: [] for table in TABLES})
        connection.execute.assert_not_called()

    def test_forward_transfer_refuses_any_existing_application_row(self):
        with self.target_engine.begin() as connection:
            connection.execute(insert(db_schema.person).values(id=999, full_name="Existing"))

        with self.assertRaises(TransferError):
            transfer_sqlite_to_postgres(self.source_path, self.target_engine)

        self.assertEqual(self.counts(self.target_engine)["person"], 1)
        self.assertEqual(self.counts(self.target_engine)["education"], 0)

    def test_forward_transfer_rolls_back_every_table_on_insert_failure(self):
        from scripts import transfer_database

        original = transfer_database.insert_table_rows

        def fail_during_import(connection, table, rows):
            if table.name == "skill":
                raise RuntimeError("injected import failure")
            original(connection, table, rows)

        with patch.object(transfer_database, "insert_table_rows", side_effect=fail_during_import):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                transfer_sqlite_to_postgres(self.source_path, self.target_engine)

        self.assertEqual(self.counts(self.target_engine), {name: 0 for name in EXPECTED_COUNTS})

    def test_reverse_transfer_creates_verified_new_sqlite_file(self):
        with self.target_engine.begin() as connection:
            for table in TABLES:
                connection.execute(insert(table), self.table_rows(self.source_engine, table))
        destination = self.root / "export.db"

        report = transfer_postgres_to_sqlite(self.target_engine, destination)

        self.assertEqual(report.table_counts, EXPECTED_COUNTS)
        self.assertTrue(destination.is_file())
        with closing(sqlite3.connect(destination)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(
                connection.execute("SELECT version_num FROM alembic_version").fetchone()[0],
                "0001_initial_schema",
            )
            for table in TABLES:
                rows = connection.execute(f"SELECT COUNT(*) FROM {table.name}").fetchone()[0]
                self.assertEqual(rows, EXPECTED_COUNTS[table.name])
        with self.assertRaises(TransferError):
            transfer_postgres_to_sqlite(self.target_engine, destination)

    def test_reverse_transfer_does_not_leave_partial_output_on_failure(self):
        from scripts import transfer_database

        original = transfer_database.insert_table_rows

        def fail_during_export(connection, table, rows):
            if table.name == "skill":
                raise RuntimeError("injected export failure")
            original(connection, table, rows)

        with self.target_engine.begin() as connection:
            for table in TABLES:
                connection.execute(insert(table), self.table_rows(self.source_engine, table))

        destination = self.root / "failed-export.db"
        with patch.object(transfer_database, "insert_table_rows", side_effect=fail_during_export):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                transfer_postgres_to_sqlite(self.target_engine, destination)

        self.assertFalse(destination.exists())

    def test_source_must_pass_sqlite_integrity_check(self):
        broken_path = self.root / "broken.db"
        broken_path.write_bytes(b"not a sqlite database")

        with self.assertRaises(TransferError):
            transfer_sqlite_to_postgres(broken_path, self.target_engine)

    def test_forward_transfer_rejects_target_missing_an_application_table(self):
        incomplete_engine = create_engine_for_url(
            f"sqlite:///{(self.root / 'incomplete.db').as_posix()}"
        )
        self.addCleanup(incomplete_engine.dispose)
        db_schema.person.create(incomplete_engine)

        with self.assertRaises(TransferError):
            transfer_sqlite_to_postgres(self.source_path, incomplete_engine)

    def test_forward_transfer_rejects_source_missing_an_application_table(self):
        with self.source_engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE link")

        with self.assertRaises(TransferError):
            transfer_sqlite_to_postgres(self.source_path, self.target_engine)

        self.assertEqual(self.counts(self.target_engine), {name: 0 for name in EXPECTED_COUNTS})


if __name__ == "__main__":
    unittest.main()
