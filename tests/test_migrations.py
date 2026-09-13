import sqlite3

import pytest

from studio.db import Migration, apply_migrations


def test_migrations_are_ordered_idempotent_and_recorded():
    conn = sqlite3.connect(":memory:")
    migrations = (
        Migration("007_example", ("CREATE TABLE example(id INTEGER PRIMARY KEY, value TEXT)",)),
        Migration("008_example_index", ("CREATE INDEX idx_example_value ON example(value)",)),
    )
    assert apply_migrations(conn, migrations) == ["007_example", "008_example_index"]
    assert apply_migrations(conn, migrations) == []
    versions = [row[0] for row in conn.execute(
        "SELECT version FROM app_schema_migrations ORDER BY version"
    )]
    assert versions == ["007_example", "008_example_index"]


def test_failed_migration_rolls_back_schema_and_version_record():
    conn = sqlite3.connect(":memory:")
    migration = Migration(
        "007_broken",
        ("CREATE TABLE should_rollback(id INTEGER)", "INSERT INTO missing_table VALUES(1)"),
    )
    with pytest.raises(sqlite3.OperationalError):
        apply_migrations(conn, (migration,))
    assert conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='should_rollback'"
    ).fetchone() is None
    assert conn.execute(
        "SELECT 1 FROM app_schema_migrations WHERE version='007_broken'"
    ).fetchone() is None


@pytest.mark.parametrize(
    "migrations",
    [
        (Migration("008_second", ("SELECT 1",)), Migration("007_first", ("SELECT 1",))),
        (Migration("007_duplicate", ("SELECT 1",)), Migration("007_duplicate", ("SELECT 1",))),
        (Migration("bad-version", ("SELECT 1",)),),
    ],
)
def test_invalid_migration_registry_is_rejected(migrations):
    with pytest.raises(ValueError):
        apply_migrations(sqlite3.connect(":memory:"), migrations)
