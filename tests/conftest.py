from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.core.config import get_settings


def run_migrations(connection: Connection) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    settings = get_settings()
    url = settings.test_database_url

    if not url:
        pytest.fail("TEST_DATABASE_URL is not configured")

    database = make_url(url)
    if database.database != "notifications_test":
        pytest.fail("Test database must be named notifications_test")
    if database.drivername != "postgresql+asyncpg":
        pytest.fail("Test database must use postgresql+asyncpg")
    if make_url(settings.database_url).database == database.database:
        pytest.fail("Test database must be different from the application database")

    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(run_migrations)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            # Session commits release a savepoint, leaving the outer transaction intact.
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                yield session
        finally:
            await transaction.rollback()
