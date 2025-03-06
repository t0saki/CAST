from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from ..models.vote import Base

# 创建数据库引擎 (使用PostgreSQL)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/little_vote"
engine = create_async_engine(DATABASE_URL, echo=True)

# 创建会话工厂
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()