"""测试配置和 fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from hypothesis import settings, HealthCheck

# Register a CI profile with reduced examples for faster test execution
settings.register_profile(
    "ci",
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
settings.load_profile("ci")

from app.core.database import Base, get_db
from app.main import app


# 使用 SQLite 内存数据库做测试
TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """每个测试前创建表，测试后清理."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """测试用 HTTP 客户端."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """测试用数据库会话."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def tx_session():
    """与请求 seam 同边界的会话（ADR-0004）.

    测试内不提交，结束时统一回滚 —— 与 `@transactional` 之前的状态一致。
    直接调用 service 的测试用它，就能在同一个未提交事务里同时断言状态跃迁与
    审计轨迹写入；这是以前只能靠 `GET /api/v1/audit-logs` 事后反查的东西。
    """
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
