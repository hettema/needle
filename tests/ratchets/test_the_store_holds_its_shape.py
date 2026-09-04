"""The migration and the models are one schema, and the store lives outside every tree.

Alembic's autogenerate compares the migrated database with the declarative
models; any difference means a column was added to one and not the other. And
the default store path is never inside this repository or a project.
"""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from infrastructure.paths import db_path
from infrastructure.schema import Base
from infrastructure.store import Store
from tests.ratchets.paths import REPO


def test_the_migration_matches_the_models(tmp_path: Path):
    store = Store(tmp_path / "shape.db")
    with store.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
    store.close()
    assert diff == [], f"migration and models disagree: {diff}"


def test_the_default_store_is_outside_the_repository(monkeypatch):
    monkeypatch.delenv("NEEDLE_DB", raising=False)
    monkeypatch.delenv("NEEDLE_DATA_DIR", raising=False)
    assert not db_path().resolve().is_relative_to(REPO)
