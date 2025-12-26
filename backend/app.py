from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import engine, Base
from backend.routes import auth_routes, profile_routes, session_routes, game_routes
from contextlib import asynccontextmanager
import logging
from backend.models import User, Profile, Session, SessionPlayer # Explicit import to ensure registration
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    logger.info("Starting up... loading models")
    logger.info(f"Detected tables in metadata: {Base.metadata.tables.keys()}")
    
    try:
        async with engine.begin() as conn:
            # Inspection: Check if 'users' table has 'password_hash' column
            # We use text() to execute raw SQL compatible with postgres/asyncpg
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='password_hash'"
            ))
            column_exists = result.scalar()
            
            if not column_exists:
                logger.warning("CRITICAL: Schema mismatch detected (missing password_hash). Resetting database...")
                await conn.run_sync(Base.metadata.drop_all)
                logger.info("Database dropped.")
            
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables checked/created successfully")
        
        # Auto-Migration: Add lobby_name column if it doesn't exist
        try:
             async with engine.begin() as conn:
                 logger.info("Checking for lobby_name column...")
                 result = await conn.execute(text(
                     "SELECT column_name FROM information_schema.columns "
                     "WHERE table_name='sessions' AND column_name='lobby_name'"
                 ))
                 column_exists = result.scalar()
                 
                 if not column_exists:
                     logger.info("Adding lobby_name column to sessions table...")
                     await conn.execute(text(
                         "ALTER TABLE sessions ADD COLUMN lobby_name VARCHAR NULL"
                     ))
                     logger.info("✓ Successfully added lobby_name column!")
                 else:
                     logger.info("✓ lobby_name column already exists.")
        except Exception as e:
            logger.error(f"Error migrating lobby_name column: {e}")
        
        # Auto-Cleanup Ghost Lobbies on Startup
        try:
             async with engine.begin() as conn:
                 logger.info("Cleaning up ghost lobbies (marking 'waiting' sessions as 'closed')...")
                 await conn.execute(text("UPDATE sessions SET status = 'closed' WHERE status = 'waiting'"))
                 logger.info("Ghost lobbies cleaned up.")
        except Exception as e:
            logger.error(f"Error cleaning up ghost lobbies: {e}")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        
    yield
    # Shutdown

app = FastAPI(title="EDU PARTY MAYHEM", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_routes.router, prefix="/api")
app.include_router(profile_routes.router, prefix="/api")
app.include_router(session_routes.router, prefix="/api")
app.include_router(game_routes.router) # WebSocket doesn't need prefix usually, or /ws

# Serve Frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
