import asyncio
import logging
from backend.database import engine, Base
from backend.models import User, Profile, Session, SessionPlayer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_database():
    logger.info("Starting database reset...")
    try:
        async with engine.begin() as conn:
            # Drop all tables
            logger.info("Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped.")
            
            # Create all tables
            logger.info("Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables created successfully.")
            
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_database())
