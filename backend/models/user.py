from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base
from pydantic import BaseModel, ConfigDict

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)
    # session_players = relationship("SessionPlayer", back_populates="user") # Circular, defined later

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
