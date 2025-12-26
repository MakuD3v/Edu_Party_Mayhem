from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from backend.services.game_service import game_service
from backend.services.lobby_service import lobby_service
from backend.services.game_session_service import game_session_service
from backend.database import get_db, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from sqlalchemy.orm import Session
from backend.config import settings
from backend.games import MathQuiz, SpeedTyping, TechSprint
from backend.models import Session as GameSessionModel, User
from typing import List, Dict
import json
import random

router = APIRouter(tags=["game"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {} # session_code -> [ws]

    async def connect(self, websocket: WebSocket, session_code: str):
        await websocket.accept()
        if session_code not in self.active_connections:
            self.active_connections[session_code] = []
        self.active_connections[session_code].append(websocket)

    def disconnect(self, websocket: WebSocket, session_code: str):
        if session_code in self.active_connections:
            self.active_connections[session_code].remove(websocket)
            if not self.active_connections[session_code]:
                del self.active_connections[session_code]

    async def broadcast(self, message: dict, session_code: str):
        # Use .get() to safely access list even if removed concurrently
        connections = self.active_connections.get(session_code)
        if connections:
            # Debug logging
            ids = [str(getattr(ws, 'user_id', '?')) for ws in connections]
            print(f"📡 Broadcasting {message.get('type')} to {len(connections)} clients in {session_code}: {ids}")
            
            # Create a copy to avoid modification during iteration issues
            for connection in connections[:]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    print(f"⚠️ Error broadcasting to client {getattr(connection, 'user_id', '?')}: {e}")
                    # Optionally remove dead connection here, but disconnect() should handle it

# In-memory session state for the prototype (Should be in Redis/DB for prod)
session_state = {} 

manager = ConnectionManager()

@router.websocket("/ws/{session_code}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, session_code: str, user_id: int):
    # Attach user_id for debugging  
    websocket.user_id = user_id
    
    # OPTIMIZED: Single DB query for both username and host_id
    user_name = f"Player {user_id}"  # Fallback
    real_host_id = user_id  # Fallback
    
    try:
        from backend.database import AsyncSessionLocal
        from sqlalchemy import select
        from backend.models import User, Session
        
        async with AsyncSessionLocal() as db:
            # Single transaction for both queries
            user_result = await db.execute(select(User).where(User.id == user_id))
            session_result = await db.execute(select(Session).where(Session.session_code == session_code))
            
            db_user = user_result.scalars().first()
            db_session = session_result.scalars().first()
            
            if db_user:
                user_name = db_user.username
            if db_session:
                real_host_id = db_session.host_id
                
        print(f"✓ Loaded user '{user_name}', host={real_host_id}")
    except Exception as e:
        print(f"⚠️ DB error: {e}, using fallbacks")
    
    # Connect IMMEDIATELY - no delays
    await manager.connect(websocket, session_code)
    
    # Check if game is already running and send ROUND_START immediately
    if session_code in session_state and "game_session" in session_state[session_code]:
        game_session = session_state[session_code]["game_session"]
        current_state = game_session.get_current_state()
        
        if current_state:
            print(f"⚡ Late join: Sending ROUND_START to user {user_id}")
            await websocket.send_text(json.dumps(current_state))
            
            # If round is ALREADY synced, tell this late user immediately!
            if game_session.is_round_synced:
                 print(f"⚡ Round is ALREADY synced. Unblocking user {user_id}...")
                 await websocket.send_text(json.dumps({
                     "type": "ALL_PLAYERS_READY",
                     "message": "Late join - unblocking immediately"
                 }))
    
    # Init Session Config if needed
    if session_code not in session_state:
        session_state[session_code] = {"players": {}, "host_id": real_host_id}
        
    # Register Player
    session_state[session_code]["players"][user_id] = {
        "user_id": user_id,
        "name": user_name,
        "is_ready": False,
        "is_host": (session_state[session_code]["host_id"] == user_id),
        "icon": "🎓" 
    }
    
    # Broadcast Join Update
    players_list = list(session_state[session_code]["players"].values())
    await manager.broadcast({"type": "PLAYER_LIST_UPDATE", "players": players_list}, session_code)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Allow raw string commands for simple testing
            msg_type = message.get("type", message) if isinstance(message, dict) else message

            if msg_type == "GET_PLAYERS":
                 players_list = list(session_state[session_code]["players"].values())
                 await manager.broadcast({"type": "PLAYER_LIST_UPDATE", "players": players_list}, session_code)

            elif msg_type == "PLAYER_READY":
                is_ready = message.get("is_ready", True)
                if user_id in session_state[session_code]["players"]:
                    session_state[session_code]["players"][user_id]["is_ready"] = is_ready
                
                # Broadcast Update
                players_list = list(session_state[session_code]["players"].values())
                await manager.broadcast({"type": "PLAYER_LIST_UPDATE", "players": players_list}, session_code)
            
            elif msg_type == "START_GAME":
                # Check if host
                 actual_host = session_state[session_code]["host_id"]
                 print(f"DEBUG: START_GAME received from {user_id}. Host is {actual_host}. Msg: {message}")
                 
                 if actual_host == user_id:
                     # Host is implicitly ready if they click Start
                     if user_id in session_state[session_code]["players"]:
                         session_state[session_code]["players"][user_id]["is_ready"] = True
                         
                     force_test = message.get("force_test", False)
                     
                     # Check DEV MODE bypass or ALL READY
                     all_ready = all(p["is_ready"] for p in session_state[session_code]["players"].values())
                     player_count = len(session_state[session_code]["players"])
                     
                     should_start = False
                     if force_test:
                         # Test mode: Allow solo play (1+ players)
                         should_start = True
                         print(f"✓ Force starting session {session_code} (Test Mode) with {player_count} player(s)")
                     elif (all_ready and player_count >= 2):
                         should_start = True
                         print(f"✓ Starting session {session_code} - all players ready")
                     elif settings.DEV_MODE:
                         should_start = True
                         print(f"✓ Starting session {session_code} (DEV_MODE)")
                     
                     if should_start: 
                        print(f"🎮 Starting game session for {session_code}")
                        
                        try:
                            # Get players list
                            players = list(session_state[session_code]["players"].values())
                            print(f"   Players: {[p['name'] for p in players]}")
                            
                            # Start game session with full round management
                            game_session = await game_session_service.start_session(
                                session_code, 
                                players,
                                manager,
                                is_test_mode=force_test
                            )
                            
                            # Store session reference
                            session_state[session_code]["game_session"] = game_session
                            
                            # Update DB status so polling works for late/sync-failed clients
                            try:
                                async with AsyncSessionLocal() as db:
                                    await db.execute(
                                        update(GameSessionModel)
                                        .where(GameSessionModel.session_code == session_code)
                                        .values(status='playing')
                                    )
                                    await db.commit()
                                print(f"✓ Updated DB status to 'playing' for {session_code}")
                            except Exception as e:
                                print(f"⚠️ Failed to update DB status: {e}")
                            
                            # Force broadcast GAME_START
                            print(f"📣 Force broadcasting GAME_START for {session_code}")
                            await manager.broadcast({
                                "type": "GAME_START",
                                "session_code": session_code
                            }, session_code)
                            
                            print(f"✓ Game session started successfully for {session_code}")
                        except Exception as e:
                            print(f"❌ ERROR starting game session for {session_code}: {e}")
                            import traceback
                            traceback.print_exc()
                            await websocket.send_text(json.dumps({
                                "type": "ERROR",
                                "message": f"Failed to start game: {str(e)}"
                            }))
                     else:
                         # Send error/warning to host
                         await websocket.send_text(json.dumps({
                             "type": "ERROR",
                             "message": f"Cannot start: Need at least 2 players and all ready (current: {player_count} players, all_ready: {all_ready})"
                         }))

            elif msg_type == "ROUND_COMPLETE":
                # Player finished the round (for Race Mode)
                print(f"🏁 ROUND_COMPLETE received from {user_id}")
                if "game_session" in session_state[session_code]:
                    game_session = session_state[session_code]["game_session"]
                    score = message.get("score", 0)
                    
                    # Trigger Race Logic
                    await game_session.handle_player_finish(user_id, score)
                else:
                    print(f"⚠️ ROUND_COMPLETE ignore - game session not found for {session_code}")

            elif msg_type == "GAME_ACTION":
                # Handle game actions (answers, progress, etc.)
                # Removed incorrect score tracking - frontend validates correctness
                # Final score comes from ROUND_COMPLETE message
                pass
            
            elif msg_type == "GET_GAME_STATE":
                # Resend the current game state (ROUND_START) if active
                if "game_session" in session_state[session_code]:
                    game_session = session_state[session_code]["game_session"]
                    current_state = game_session.get_current_state()
                    if current_state:
                        print(f"✓ Resending game state (ROUND_START) to user {user_id} - fallback for missed broadcast")
                        await websocket.send_text(json.dumps(current_state))
                    else:
                        print(f"⚠️ Game session exists but no current state available for user {user_id}")
                else:
                    print(f"⚠️ GET_GAME_STATE requested by user {user_id} but no active game session found")
            
            elif msg_type == "PLAYER_READY_FOR_ROUND":
                # Player has received ROUND_START and is ready to start game sequence
                print(f"📥 PLAYER_READY_FOR_ROUND received from user {user_id} in session {session_code}")
                
                if "game_session" in session_state[session_code]:
                    game_session = session_state[session_code]["game_session"]
                    ready_count = game_session.mark_player_ready(user_id)
                    
                    print(f"   Ready count: {ready_count}/{game_session.total_expected_players}")
                    print(f"   Ready players: {game_session.players_ready_for_round}")
                    
                    # Check if all players are ready
                    if game_session.check_all_players_ready():
                        print(f"✅ All players ready for {session_code}! Broadcasting ALL_PLAYERS_READY...")
                        
                        # Mark as synced so late joiners don't get stuck
                        game_session.mark_round_synced()
                        
                        # Reset ready set for next round
                        game_session.reset_ready_status()
                        
                        # Broadcast to all clients to start game sequence
                        await manager.broadcast({
                            "type": "ALL_PLAYERS_READY",
                            "message": "All players synchronized! Starting game..."
                        }, session_code)
                        print(f"✓ ALL_PLAYERS_READY broadcasted to session {session_code}")
                    else:
                        print(f"⏳ Waiting for more players: {ready_count}/{game_session.total_expected_players}")
                else:
                    print(f"⚠️ PLAYER_READY_FOR_ROUND received but no active game session for {session_code}")
            
            elif msg_type == "ROUND_COMPLETE":
                # Player has finished round (time up or goal met)
                if "game_session" in session_state[session_code]:
                    game_session = session_state[session_code]["game_session"]
                    score = msg.get("score", 0)
                    print(f"📥 ROUND_COMPLETE from User {user_id}: Score {score}")
                    
                    # Record score and check for round completion
                    await game_session.handle_player_finish(user_id, score)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_code)
        
        if session_code in session_state and user_id in session_state[session_code]["players"]:
            del session_state[session_code]["players"][user_id]
            
            # Auto-Dissolve if empty - UPDATE DATABASE FIRST
            game_active = "game_session" in session_state[session_code]
            
            if not session_state[session_code]["players"] and not game_active:
                print(f"Session {session_code} is empty and NO game active. Dissolving...")
                
                # Update DB to close session BEFORE clearing memory
                from backend.database import AsyncSessionLocal
                from sqlalchemy import update
                from backend.models import Session
                
                try:
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Session)
                            .where(Session.session_code == session_code)
                            .values(status="closed")
                        )
                        await db.commit()
                        print(f"✓ Session {session_code} marked as closed in DB.")
                except Exception as e:
                    print(f"✗ ERROR closing session in DB: {e}")
                    # Still clean up memory even if DB update fails
                
                # Now clean up in-memory state
                del session_state[session_code]
                print(f"✓ Session {session_code} removed from memory.")

            else:
                # Broadcast updated player list to remaining players
                players_list = list(session_state[session_code]["players"].values())
                await manager.broadcast({"type": "PLAYER_LIST_UPDATE", "players": players_list}, session_code)
