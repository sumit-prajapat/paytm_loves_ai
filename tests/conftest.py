import os
import tempfile

# Tests are fully offline and deterministic: no provider keys, mock LLM/STT/TTS (R9).
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "DEMO_MODE": "true",
    "GEMINI_API_KEY": "",
    "SARVAM_API_KEY": "",
    "LLM_PROVIDER": "mock",
    "STT_PROVIDER": "mock",
    "TTS_PROVIDER": "mock",
    "AUDIO_DIR": os.path.join(tempfile.gettempdir(), "saarthi_test_audio"),
    "HOUSEKEEPING_ENABLED": "false",
    "DEBUG": "false",
})

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.agents.action import validator_stats  # noqa: E402
from app.core.cache import cache  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.llm.gateway import llm_gateway  # noqa: E402
from app.main import app  # noqa: E402
from app.services.kill_switch import kill_switch_service  # noqa: E402

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
TestAsyncSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# SQL capture registered BEFORE any connection exists (engine events only attach to new connections).
SQL_LOG: list[tuple[str, str]] = []


def _capture(conn, cursor, statement, parameters, context, executemany):
    SQL_LOG.append((statement.lower(), str(parameters)))


from sqlalchemy import event  # noqa: E402

from app.db.session import engine as _app_engine  # noqa: E402

for _eng in (test_engine, _app_engine):
    event.listen(_eng.sync_engine, "before_cursor_execute", _capture)

HERO_USERS = {
    "ramesh": {"sub": "usr_ramesh", "username": "merchant_ramesh", "role": "merchant", "merchant_id": "m_ramesh"},
    "sunita": {"sub": "usr_sunita", "username": "merchant_sunita", "role": "merchant", "merchant_id": "m_sunita"},
    "gupta": {"sub": "usr_gupta", "username": "merchant_gupta", "role": "merchant", "merchant_id": "m_disputed"},
    "arjun": {"sub": "usr_arjun", "username": "traveller_arjun", "role": "traveller", "customer_id": "c_arjun"},
    "meena": {"sub": "usr_meena", "username": "traveller_meena", "role": "traveller", "customer_id": "c_meena"},
    "ops": {"sub": "usr_ops", "username": "ops_agent_1", "role": "ops_agent"},
    "admin": {"sub": "usr_admin", "username": "admin_user", "role": "admin"},
}


def auth(who: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(HERO_USERS[who])}"}


@pytest.fixture(autouse=True)
def reset_process_state():
    from app.core.middleware import _RATE_LIMIT_BUCKETS
    _RATE_LIMIT_BUCKETS.clear()
    cache.clear()
    llm_gateway.stats.clear()
    llm_gateway.set_adapter(None)
    validator_stats.clear()
    kill_switch_service._is_active = False
    yield
    kill_switch_service._is_active = False
    llm_gateway.set_adapter(None)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession):
    from app.db.seed import seed_database
    await seed_database(db_session, merchant_count=3)
    return db_session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
