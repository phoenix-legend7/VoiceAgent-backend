from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from contextlib import asynccontextmanager

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_size=20,  # Increased pool size
    max_overflow=30,  # Increased max overflow
    pool_timeout=30,
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=1800,  # Recycle connections after 30 minutes
)

# Regular session factory for request handlers
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevent expired object issues
)

# Background session factory with different settings
BackgroundSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@asynccontextmanager
async def get_db_background():
    """Context manager for background tasks that need database access"""
    session = BackgroundSessionLocal()
    try:
        yield session
    finally:
        await session.close()
