from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base
from pydantic import BaseModel, ConfigDict

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    display_name = Column(String)
    icon_id = Column(String, default="default")
    border_style = Column(String, default="default")
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    icon_id: str | None = None
    border_style: str | None = None

class ProfileResponse(BaseModel):
    display_name: str | None = None
    icon_id: str
    border_style: str

    model_config = ConfigDict(from_attributes=True)
