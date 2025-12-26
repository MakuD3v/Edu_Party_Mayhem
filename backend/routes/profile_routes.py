from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db
from backend.models import User, Profile, ProfileUpdate, ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])

# Dependency to get current user would go here for real auth
# For simplicity in this scaffold, passing user_id or assuming handling via token dependency
# I'll add a simplified "get_profile" by user_id for now

@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.patch("/{user_id}", response_model=ProfileResponse)
async def update_profile(user_id: int, update_data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    if update_data.display_name:
        profile.display_name = update_data.display_name
    if update_data.icon_id:
        profile.icon_id = update_data.icon_id
    if update_data.border_style:
        profile.border_style = update_data.border_style
        
    await db.commit()
    await db.refresh(profile)
    return profile
