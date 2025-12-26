from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base
from pydantic import BaseModel, ConfigDict

class SessionPlayer(Base):
    __tablename__ = "session_players"

    session_id = Column(Integer, ForeignKey("sessions.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    score = Column(Integer, default=0)
    is_eliminated = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="players")
    user = relationship("User")

class PlayerResponse(BaseModel):
    user_id: int
    score: int
    is_eliminated: bool
    
    model_config = ConfigDict(from_attributes=True)
