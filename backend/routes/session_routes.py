from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import SessionCreate, SessionResponse, PlayerResponse, Session
from backend.services.matchmaking_service import MatchmakingService
from backend.services.lobby_service import lobby_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = await MatchmakingService.create_session(
        db, 
        session_data.host_id, 
        session_data.max_players, 
        session_data.is_public,
        session_data.lobby_name
    )
    # Start inactivity monitor
    await lobby_service.start_tracking(session.session_code, lambda code: print(f"Session {code} dissolved"))
    return session

@router.post("/{code}/join", response_model=SessionResponse)
async def join_session(code: str, user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        session = await MatchmakingService.join_session(db, code, user_id)
        lobby_service.register_session_activity(code)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    sessions = await MatchmakingService.get_public_sessions(db)
    return sessions
