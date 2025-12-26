from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from backend.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
