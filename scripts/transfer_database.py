"""Verified, transactional transfers between SQLite and PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, Table, inspect, insert, select, text
from sqlalchemy.engine import Connection, URL

import db_schema
from database import create_engine_for_url, database_url_from_env, get_engine


APPLICATION_TABLES: tuple[Table, ...] = (
    db_schema.person,
    db_schema.education,
    db_schema.experience,
    db_schema.project,
    db_schema.skill,
    db_schema.certification,
    db_schema.volunteer_experience,
    db_schema.link,
)
ROOT = Path(__file__).resolve().parent.parent


class TransferError(ValueError):
    """Raised when a database transfer fails a safety or fidelity check."""


@dataclass(frozen=True)
class TransferReport:
    table_counts: dict[str, int]
    table_digests: dict[str, str]


def _require_application_tables(connection: Connection) -> None:
    present = set(inspect(connection).get_table_names())
    missing = [table.name for table in APPLICATION_TABLES if table.name not in present]
    if missing:
        raise TransferError(
            "Database is missing application tables: " + ", ".join(missing)
        )


def _sqlite_source_engine(sqlite_path: Path) -> Engine:
    path = Path(sqlite_path).expanduser().resolve()
    if not path.is_file():
        raise TransferError("SQLite source database does not exist as a file.")
    engine = create_engine_for_url(
        URL.create(
            "sqlite",
            database=f"file:{path.as_posix()}",
            query={"mode": "ro", "uri": "true"},
        )
    )
    try:
        with engine.connect() as connection:
            result = connection.exec_driver_sql("PRAGMA integrity_check").all()
            if len(result) != 1 or result[0][0] != "ok":
                raise TransferError("SQLite source failed PRAGMA integrity_check.")
            _require_application_tables(connection)
    except TransferError:
        engine.dispose()
        raise
    except Exception as exc:
        engine.dispose()
        raise TransferError("SQLite source could not be validated.") from exc
    return engine


def _read_rows(connection: Connection) -> dict[str, list[dict[str, object]]]:
    _require_application_tables(connection)
    return {
        table.name: [
            dict(row)
            for row in connection.execute(select(table).order_by(table.c.id)).mappings()
        ]
        for table in APPLICATION_TABLES
    }


def _canonical_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for row in rows:
        values = dict(row)
        if "is_current" in values:
            value = values["is_current"]
            values["is_current"] = None if value is None else bool(value)
        normalized.append(values)
    return normalized


def _report(rows_by_table: Mapping[str, Sequence[Mapping[str, object]]]) -> TransferReport:
    counts = {table.name: len(rows_by_table[table.name]) for table in APPLICATION_TABLES}
    digests = {}
    for table in APPLICATION_TABLES:
        canonical = _canonical_rows(rows_by_table[table.name])
        encoded = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        digests[table.name] = hashlib.sha256(encoded).hexdigest()
    return TransferReport(table_counts=counts, table_digests=digests)


def insert_table_rows(
    connection: Connection,
    table: Table,
    rows: Sequence[Mapping[str, object]],
) -> None:
    """Single insertion seam used by both directions and rollback tests."""
    if rows:
        connection.execute(insert(table), list(rows))


def _assert_empty_target(connection: Connection) -> None:
    _require_application_tables(connection)
    for table in APPLICATION_TABLES:
        count = connection.scalar(select(text("count(*)")).select_from(table))
        if count:
            raise TransferError(
                f"Import target is not empty: application table {table.name} has rows."
            )


def _advance_postgresql_sequences(connection: Connection, rows_by_table: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
    for table in APPLICATION_TABLES:
        ids = [int(row["id"]) for row in rows_by_table[table.name] if row["id"] is not None]
        if not ids:
            continue
        connection.execute(
            text("SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :max_id, true)"),
            {"table_name": table.name, "max_id": max(ids)},
        )


def _write_to_target(engine: Engine, rows_by_table: Mapping[str, Sequence[Mapping[str, object]]]) -> None:
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            table_list = ", ".join(table.name for table in APPLICATION_TABLES)
            connection.exec_driver_sql(f"LOCK TABLE {table_list} IN ACCESS EXCLUSIVE MODE")
        _assert_empty_target(connection)
        for table in APPLICATION_TABLES:
            insert_table_rows(connection, table, rows_by_table[table.name])
        if engine.dialect.name == "postgresql":
            _advance_postgresql_sequences(connection, rows_by_table)


def transfer_sqlite_to_postgres(sqlite_path: Path, target_engine: Engine) -> TransferReport:
    """Copy a verified SQLite database into a schema-initialized empty target."""
    source_engine = _sqlite_source_engine(Path(sqlite_path))
    try:
        with source_engine.connect() as connection:
            rows_by_table = _read_rows(connection)
        report = _report(rows_by_table)
        _write_to_target(target_engine, rows_by_table)
        return report
    finally:
        source_engine.dispose()


def _apply_sqlite_migrations(sqlite_path: Path) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    database_url = URL.create("sqlite", database=str(sqlite_path.resolve()))
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {"APP_ENV": "development", "DATABASE_URL": database_url.render_as_string()},
    ):
        command.upgrade(config, "head")


def _publish_new_file(temp_path: Path, destination: Path) -> None:
    # A same-directory hard link is atomic and fails if destination appeared meanwhile.
    os.link(temp_path, destination)
    temp_path.unlink()


def transfer_postgres_to_sqlite(source_engine: Engine, sqlite_path: Path) -> TransferReport:
    """Export to a new, validated SQLite file without replacing existing files."""
    destination = Path(sqlite_path).expanduser().resolve()
    if destination.exists():
        raise TransferError("SQLite destination already exists; refusing to overwrite it.")
    if not destination.parent.is_dir():
        raise TransferError("SQLite destination directory does not exist.")

    with source_engine.connect() as connection:
        rows_by_table = _read_rows(connection)
    report = _report(rows_by_table)

    file_descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp.db", dir=destination.parent
    )
    os.close(file_descriptor)
    temp_path = Path(temp_name)
    temp_path.unlink()
    try:
        _apply_sqlite_migrations(temp_path)
        target_engine = create_engine_for_url(URL.create("sqlite", database=str(temp_path)))
        try:
            _write_to_target(target_engine, rows_by_table)
            with target_engine.connect() as connection:
                exported_rows = _read_rows(connection)
            if _report(exported_rows) != report:
                raise TransferError("SQLite export verification did not match its source.")
            with target_engine.connect() as connection:
                integrity = connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
            if integrity != "ok":
                raise TransferError("SQLite export failed PRAGMA integrity_check.")
        finally:
            target_engine.dispose()
        _publish_new_file(temp_path, destination)
        return report
    finally:
        if temp_path.exists():
            temp_path.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--direction",
        required=True,
        choices=("sqlite-to-postgres", "postgres-to-sqlite"),
    )
    parser.add_argument("--sqlite-path", required=True, type=Path)
    args = parser.parse_args(argv)

    url = database_url_from_env()
    if url.get_backend_name() != "postgresql":
        parser.error("DATABASE_URL must point to PostgreSQL for database transfers.")
    engine = get_engine()
    try:
        if args.direction == "sqlite-to-postgres":
            report = transfer_sqlite_to_postgres(args.sqlite_path, engine)
        else:
            report = transfer_postgres_to_sqlite(engine, args.sqlite_path)
    except TransferError as exc:
        parser.exit(1, f"Transfer refused or failed: {exc}\n")
    except Exception:
        # Driver exceptions can include connection details; keep the CLI output sanitized.
        parser.exit(1, "Transfer failed. Review the database and filesystem configuration.\n")
    finally:
        engine.dispose()
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
