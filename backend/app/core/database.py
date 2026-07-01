"""数据库连接管理."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_engine = None
_session_factory = None


def get_engine():
    """懒加载数据库引擎."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=20,
            max_overflow=10,
            pool_recycle=3600,
        )
    return _engine


def get_session_factory():
    """懒加载会话工厂."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类."""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话（依赖注入用）."""
    async with get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()
