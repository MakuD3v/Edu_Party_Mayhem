from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base
from pydantic import BaseModel, ConfigDict
from typing import List

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_code = Column(String, unique=True, index=True)
    lobby_name = Column(String, nullable=True)  # Custom lobby name
    host_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="waiting") # waiting, active, finished, closed
    max_players = Column(Integer, default=50)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    players = relationship("SessionPlayer", back_populates="session", cascade="all, delete-orphan")

class SessionCreate(BaseModel):
    host_id: int
    max_players: int = 50
    is_public: bool = True
    lobby_name: str | None = None  # Optional custom lobby name

class SessionResponse(BaseModel):
    session_code: str
    lobby_name: str | None = None
    status: str
    max_players: int
    is_public: bool
    
    model_config = ConfigDict(from_attributes=True)
