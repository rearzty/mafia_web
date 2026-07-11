from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with SessionLocal() as db:
        yield db
