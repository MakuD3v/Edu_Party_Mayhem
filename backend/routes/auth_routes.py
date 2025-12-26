from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db
from backend.models import User, UserCreate, UserResponse, Profile
from backend.services.auth_service import AuthService
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

import logging

logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Registration attempt for username: {user.username}")
    try:
        # Check existing
        result = await db.execute(select(User).where(User.username == user.username))
        if result.scalars().first():
            logger.warning(f"Registration failed: Username {user.username} exists")
            raise HTTPException(status_code=400, detail="Username already registered")
        
        logger.info("Hashing password...")
        hashed_pwd = AuthService.get_password_hash(user.password)
        
        logger.info("Creating user object...")
        new_user = User(username=user.username, password_hash=hashed_pwd)
        db.add(new_user)
        
        logger.info("Flushing to DB to generate ID...")
        await db.flush() 
        logger.info(f"User created with ID: {new_user.id}")
        
        # Create default profile
        logger.info("Creating default profile...")
        new_profile = Profile(user_id=new_user.id, display_name=new_user.username)
        db.add(new_profile)
        
        logger.info("Committing transaction...")
        await db.commit()
        await db.refresh(new_user)
        logger.info("Registration successful")
        
        return new_user
    except Exception as e:
        logger.error(f"Registration CRITICAL error: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalars().first()
    
    if not db_user or not AuthService.verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = AuthService.create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user_id": db_user.id}

@router.get("/debug")
async def debug_auth():
    try:
        test_pw = "TestPass123!"
        hashed = AuthService.get_password_hash(test_pw)
        valid = AuthService.verify_password(test_pw, hashed)
        return {
            "status": "ok",
            "hashing_works": valid,
            "hash_sample": hashed[:10] + "..."
        }
    except Exception as e:
        logger.error(f"Debug failed: {e}", exc_info=True)
        return {"status": "error", "details": str(e)}
