import asyncio
from backend.database import AsyncSessionLocal
from sqlalchemy import text

async def cleanup():
    async with AsyncSessionLocal() as db:
        print("Cleaning up stale sessions...")
        # Mark all waiting sessions as closed
        await db.execute(text("UPDATE sessions SET status = 'closed' WHERE status = 'waiting'"))
        await db.commit()
        print("All waiting sessions marked as closed.")

if __name__ == "__main__":
    asyncio.run(cleanup())
