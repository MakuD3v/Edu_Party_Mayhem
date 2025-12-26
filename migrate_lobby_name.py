"""
Database migration script to add lobby_name column to sessions table.
Run this script to update your production database.
"""
import asyncio
import os
from sqlalchemy import text
from backend.database import engine

async def migrate():
    """Add lobby_name column to sessions table if it doesn't exist."""
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='sessions' AND column_name='lobby_name'"
        ))
        column_exists = result.scalar()
        
        if not column_exists:
            print("Adding lobby_name column to sessions table...")
            await conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN lobby_name VARCHAR NULL"
            ))
            print("✓ Successfully added lobby_name column!")
        else:
            print("✓ lobby_name column already exists, skipping migration.")

if __name__ == "__main__":
    print("Starting database migration...")
    asyncio.run(migrate())
    print("Migration complete!")
