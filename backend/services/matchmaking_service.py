from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import Session, SessionPlayer, User
import uuid
import random
import string

class MatchmakingService:
    @staticmethod
    def generate_session_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    @staticmethod
    async def create_session(db: AsyncSession, host_id: int, max_players: int = 50, is_public: bool = True, lobby_name: str | None = None) -> Session:
        code = MatchmakingService.generate_session_code()
        new_session = Session(
            session_code=code,
            lobby_name=lobby_name,
            host_id=host_id,
            max_players=max_players,
            is_public=is_public,
            status="waiting"
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    @staticmethod
    async def join_session(db: AsyncSession, session_code: str, user_id: int) -> Session:
        result = await db.execute(select(Session).where(Session.session_code == session_code))
        session = result.scalars().first()
        
        if not session:
            raise ValueError("Session not found")
            
        if session.status != "waiting":
            raise ValueError("Session already started")
            
        # Check player count (need to load players or count query)
        # For simplicity assuming naive check or we add a count query here.
        # Ideally using select(func.count())...
        
        # Check if already joined
        result_player = await db.execute(select(SessionPlayer).where(
            SessionPlayer.session_id == session.id, 
            SessionPlayer.user_id == user_id
        ))
        existing_player = result_player.scalars().first()
        
        if not existing_player:
            new_player = SessionPlayer(session_id=session.id, user_id=user_id)
            db.add(new_player)
            await db.commit()
            
        return session

    @staticmethod
    async def get_public_sessions(db: AsyncSession):
        result = await db.execute(select(Session).where(Session.is_public == True, Session.status == "waiting"))
        return result.scalars().all()
