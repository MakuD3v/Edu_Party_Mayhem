import os
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/eduparty")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v: str):
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEV_MODE: bool = False # set via env var in prod if needed

settings = Settings()
