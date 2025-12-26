"""
Game Session Service - Orchestrates multi-round game sessions with elimination
"""
import random
import asyncio
from typing import Dict, List, Any
from backend.games import MathQuiz, SpeedTyping, TechSprint, TrueFalse, FixSyntax

class GameSession:
    """Represents a single game session with multiple rounds"""
    
    def __init__(self, session_code: str, players: List[Dict], manager, is_test_mode: bool = False):
        self.session_code = session_code
        self.manager = manager
        self.current_round = 1
        self.total_rounds = 3  # 3 rounds, random selection from 5 games
        self.active_players = players.copy()
        self.eliminated_players = []
        self.game_history = []  # Track which games have been played
        self.available_games = [MathQuiz, SpeedTyping, TechSprint, TrueFalse, FixSyntax]
        self.current_game_config = None
        self.is_test_mode = is_test_mode # Store test mode flag
        self.current_game_mode = None  # "race" or "timed" - set in start_round()
        self.round_timer_task = None  # Track backend timer for timed games
        
        # Player synchronization tracking
        self.players_ready_for_round = set()  # Track which players confirmed ready
        self.total_expected_players = len(players)
        self.is_round_synced = False # Track if current round has synced
        
        # Battle Royale / Race Logic
        self.finished_players = [] # List of user_ids who finished/qualified
        self.slots_available = len(players) # Default to all

    def get_current_state(self):
        """Get the current state of the game session for reconnects"""
        if not self.current_game_config:
            return None
            
        return {
            "type": "ROUND_START",
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "active_players": len(self.active_players),
            "eliminated_count": len(self.eliminated_players),
            "is_test_mode": self.is_test_mode,
            "slots_available": self.slots_available, # Include slots info
            "is_synced": self.is_round_synced, # Send sync status
            **self.current_game_config
        }
        
    async def start_round(self):
        """Start a new round"""
        print(f"Starting Round {self.current_round} for session {self.session_code}")
        
        try:
            # Strict usage of active_players for sync
            self.total_expected_players = len(self.active_players)
            self.is_round_synced = False
            print(f"   [Sync] Strictly expecting {self.total_expected_players} players to sync")
            
            # Reset finishers for new round
            self.finished_players = []
            self.round_results = {} # Reset specific results (score/time)
            
            # Calculate Slots for this round
            total_active = len(self.active_players)
            
            if self.current_round < self.total_rounds:
                # Intermediate Rounds
                if self.current_round == 1:
                    # R1: Aim for 75%
                    raw_slots = int(total_active * 0.75)
                else:
                    # R2+: Aim for 50%
                    raw_slots = int(total_active * 0.50)
                
                # Soft Floor: If we have >2 players, ensure at least 2 qualify to keep the race going
                if total_active > 2:
                    self.slots_available = max(raw_slots, 2)
                else:
                    # If 2 players, R1 must eliminate 1 to make progress (2->1)
                    # Unless we want a non-elimination round? 
                    # No, Battle Royale implies elimination.
                    self.slots_available = max(1, raw_slots)
                    
                # Ensure we strictly eliminate at least 1 person per round if possible
                # (Don't let slots == total_active)
                if self.slots_available >= total_active and total_active > 1:
                    self.slots_available = total_active - 1
            else:
                # Final Round: Winner takes all
                self.slots_available = 1
                
            # Final safeguard
            self.slots_available = max(1, self.slots_available)
                
            print(f"   [Logic] Active: {total_active}, Available Slots: {self.slots_available}")

            # Select a random game that hasn't been played yet
            print(f"   [Step 2] Selecting game...")
            game_class = self.select_game()
            print(f"   [Step 2] Selected: {game_class.__name__}")
            self.game_history.append(game_class.__name__)
            
            # Create game instance
            print(f"   [Step 3] Instantiating game...")
            game_instance = game_class()
            
            # Get game configuration
            print(f"   [Step 4] Generating config...")
            game_config = self.get_game_config(game_instance)
            self.current_game_config = game_config  # Store for late joiners/reconnects
            
            # Detect and store game mode
            self.current_game_mode = game_config.get("mode", "timed")
            # If no explicit mode, use heuristics:
            # - Has time_limit (and not win_score) = "timed"
            # - Has win_score = "race"
            if "mode" not in game_config:
                if game_config.get("time_limit") and not game_config.get("win_score"):
                    self.current_game_mode = "timed"
                elif game_config.get("win_score"):
                    self.current_game_mode = "race"
            print(f"   [Mode] Game mode detected: {self.current_game_mode}")
            
            # Start backend timer for timed games
            if self.current_game_mode == "timed" and game_config.get("time_limit"):
                time_limit = game_config["time_limit"]
                # Add buffer for Frontend Intro (3s) + Tutorial (5s) + Countdown (3s) + Network
                adjusted_limit = time_limit + 15 
                print(f"   [Timer] Starting {adjusted_limit}s backend timer ({time_limit}s + 15s buffer)")
                self.round_timer_task = asyncio.create_task(self._round_timer(adjusted_limit))
            
            # Broadcast round start
            print(f"   [Step 5] Broadcasting ROUND_START...")
            await self.manager.broadcast({
                "type": "ROUND_START",
                "round": self.current_round,
                "total_rounds": self.total_rounds,
                "active_players": len(self.active_players),
                "eliminated_count": len(self.eliminated_players),
                "is_test_mode": self.is_test_mode,
                "slots_available": self.slots_available,
                **game_config
            }, self.session_code)
            print(f"✅ ROUND_START broadcast sent.")
            
            return game_instance
        except Exception as e:
            print(f"❌ CRITICAL ERROR in start_round: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    async def _round_timer(self, time_limit: int):
        """Backend timer for timed games - ensures round ends even if players don't submit"""
        try:
            await asyncio.sleep(time_limit)
            print(f"⏰ Timer expired for timed game!")
            
            # Wait 2 seconds for frontend to send ROUND_COMPLETE with final scores
            print(f"⏳ Waiting 2s for players to send final scores...")
            await asyncio.sleep(2)
            
            print(f"🛑 Grace period ended, force ending round...")
            await self.complete_round()
        except asyncio.CancelledError:
            print(f"⏰ Timer cancelled (round ended early)")
    
    async def handle_player_finish(self, user_id: int, score: int = 0):
        """Called when a player completes the objective (Race Logic) OR submits score (Timed Logic)"""
        import time
        arrival_time = time.time()
        
        # Check if already finished
        is_new_finish = user_id not in self.finished_players
        
        # Store Result - Track: Score, Arrival Time
        if not hasattr(self, 'round_results'):
            self.round_results = {}
            
        self.round_results[user_id] = {
            "score": score,
            "time": arrival_time,
            "finished": True
        }
        
        # Add to finishers list if not already there
        if is_new_finish:
            self.finished_players.append(user_id)
        
        rank = len(self.finished_players)
        print(f"🏁 Player {user_id} finished! Score: {score}, Rank: {rank}/{len(self.active_players)} (Mode: {self.current_game_mode})")
        
        # RACE MODE: End when enough players finish (first N to complete objective)
        if self.current_game_mode == "race":
            if len(self.finished_players) >= self.slots_available:
                print(f"🛑 Race mode: {self.slots_available} qualifiers reached, ending round...")
                await self.complete_round()
        
        # TIMED MODE: Wait for ALL players to submit OR timer to expire
        elif self.current_game_mode == "timed":
            total_active = len(self.active_players)
            if len(self.finished_players) >= total_active:
                print(f"🛑 Timed mode: All {total_active} players submitted, ending round...")
                # Cancel timer since all players finished
                if self.round_timer_task:
                    self.round_timer_task.cancel()
                await self.complete_round()
            else:
                print(f"⏳ Timed mode: Waiting for remaining players ({len(self.finished_players)}/{total_active})")

            
    async def calculate_and_broadcast_results(self):
        """Calculate rankings and broadcast QUALIFIED/ELIMINATED status to individual players"""
        print(f"\n🎯 Calculating results for Round {self.current_round}...")
        
        # Skip elimination for solo/test mode with 1 player
        if len(self.active_players) <= 1:
            print(f"⚠️ Skipping elimination - only {len(self.active_players)} player(s) remaining (solo/test mode)")
            # Still need to show qualified status
            for player in self.active_players:
                uid = player["user_id"]
                res = self.round_results.get(uid, {"score": 0, "time": 0})
                await self.manager.broadcast({
                    "type": "ROUND_RESULT",
                    "status": "qualified",
                    "rank": 1,
                    "score": res["score"],
                    "total_players": 1,
                    "message": "You qualified!"
                }, self.session_code)  # Broadcast to all since it's solo
            return

        # 1. Collect Results for ALL active players
        # 1. Collect Results for ALL active players
        submitted_results = []
        non_submitted_players = []
        
        if not hasattr(self, 'round_results'):
            self.round_results = {}
            
        for player in self.active_players:
            uid = player["user_id"]
            
            # Check if player actually submitted (is in finished_players or has a result)
            if uid in self.finished_players or uid in self.round_results:
                res = self.round_results.get(uid, {"score": 0, "time": float('inf')})
                submitted_results.append({
                    "user_id": uid,
                    "score": res.get("score", 0),
                    "time": res.get("time", float('inf')),
                    "player": player
                })
            else:
                # Player didn't submit - auto-eliminate
                non_submitted_players.append({
                    "user_id": uid,
                    "score": 0,
                    "time": float('inf'),
                    "player": player
                })
        
        print(f"📊 {len(submitted_results)} submitted, {len(non_submitted_players)} didn't submit")
        
        # 2. Sort ONLY submitted players by Score (DESC) then Time (ASC)
        submitted_results.sort(key=lambda x: (-x["score"], x["time"]))
        
        # 3. Determine qualifiers - only from those who submitted
        qualifiers_count = max(1, min(self.slots_available, len(submitted_results)))
        
        qualifiers = submitted_results[:qualifiers_count]
        eliminated_from_submitted = submitted_results[qualifiers_count:]
        
        # 4. All non-submitters are automatically eliminated
        all_eliminated = eliminated_from_submitted + non_submitted_players
        
        # Combine for full ranking display
        all_results = submitted_results + non_submitted_players
        
        print(f"📊 Rankings:")
        for i, r in enumerate(all_results):
            if i < len(qualifiers):
                status = "✅ QUALIFIED"
            else:
                status = "❌ ELIMINATED"
            submitted = "(submitted)" if r in submitted_results else "(NO SUBMIT)"
            print(f"   #{i+1}: User {r['user_id']} - Score: {r['score']}, Time: {r['time']:.3f} - {status} {submitted}")
        
        # 5. Broadcast individual results to each player
        for i, result in enumerate(all_results):
            rank = i + 1
            is_qualified = result in qualifiers  # Check if in qualifiers list
            
            # Send targeted message to this specific player
            message_data = {
                "type": "ROUND_RESULT",
                "status": "qualified" if is_qualified else "eliminated",
                "rank": rank,
                "score": result["score"],
                "total_players": len(all_results),
                "qualifiers_count": len(qualifiers),
                "message": f"You qualified! (Rank #{rank})" if is_qualified else f"You were eliminated (Rank #{rank})"
            }
            
            # Broadcast to everyone so each client can check if it's them
            await self.manager.broadcast({
                **message_data,
                "user_id": result["user_id"]  # Include user_id so client knows who this is for
            }, self.session_code)
        
        # 6. Update active/eliminated player lists
        to_eliminate = [r["player"] for r in all_eliminated]
        
        if to_eliminate:
            eliminated_ids = [p["user_id"] for p in to_eliminate]
            self.eliminated_players.extend(to_eliminate)
            self.active_players = [p for p in self.active_players if p not in to_eliminate]
            print(f"✂️ Eliminated {len(eliminated_ids)} players. {len(self.active_players)} remaining.")

    
    def select_game(self):
        """Select a random game that hasn't been played yet"""
        available = [g for g in self.available_games if g.__name__ not in self.game_history]
        if not available:
            # All games played, reset
            available = self.available_games
            self.game_history = []
        return random.choice(available)
    
    def get_game_config(self, game_instance) -> Dict[str, Any]:
        """Get game configuration from the game instance"""
        # Delegate configuration generation to the game class itself
        # This allows each game to define its own rules, timers, and content
        print(f"   [Config] Generating config for {game_instance.get_game_name()} via .start()")
        return game_instance.start(self.active_players) # Should not happen
    
    def mark_player_ready(self, user_id: int):
        """Mark a player as ready for the current round"""
        self.players_ready_for_round.add(user_id)
        ready_count = len(self.players_ready_for_round)
        print(f"✓ Player {user_id} ready for round. Total: {ready_count}/{self.total_expected_players}")
        return ready_count
    
    def check_all_players_ready(self) -> bool:
        """Check if all players have confirmed ready for current round"""
        ready_count = len(self.players_ready_for_round)
        return ready_count >= self.total_expected_players
    
    def mark_round_synced(self):
        """Mark the current round as synchronized (all players ready)"""
        self.is_round_synced = True
        print(f"   [Sync] Round {self.current_round} marked as SYNCED")

    def reset_ready_status(self):
        """Reset ready tracking for next round"""
        print(f"Resetting ready status for {self.session_code}")
        self.players_ready_for_round.clear()
    
    def generate_math_questions(self) -> List[Dict]:
        """Generate random math questions"""
        questions = []
        for i in range(5):
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            operation = random.choice(['+', '-', '*'])
            
            if operation == '+':
                answer = a + b
            elif operation == '-':
                answer = a - b
            else:
                answer = a * b
            
            # Generate wrong options
            options = [answer]
            while len(options) < 4:
                wrong = answer + random.randint(-10, 10)
                # Allow negative options if the answer is negative
                if wrong not in options:
                    options.append(wrong)
            
            random.shuffle(options)
            
            questions.append({
                "text": f"What is {a} {operation} {b}?",
                "options": [str(o) for o in options],
                "answer": str(answer)
            })
        
        return questions
    
    def generate_tech_questions(self) -> List[Dict]:
        """Generate tech/coding questions"""
        questions = [
            {
                "text": "What does HTML stand for?",
                "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Home Tool Markup Language", "Hyperlinks and Text Markup Language"],
                "answer": "Hyper Text Markup Language"
            },
            {
                "text": "Which language is used for styling web pages?",
                "options": ["CSS", "HTML", "Python", "JavaScript"],
                "answer": "CSS"
            },
            {
                "text": "What does CPU stand for?",
                "options": ["Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Central Processor Utility"],
                "answer": "Central Processing Unit"
            },
            {
                "text": "Which of these is a programming language?",
                "options": ["Python", "Eagle", "Falcon", "Sparrow"],
                "answer": "Python"
            },
            {
                "text": "What is the result of 2 ** 3 in Python?",
                "options": ["8", "6", "9", "5"],
                "answer": "8"
            }
        ]
        return random.sample(questions, min(5, len(questions)))
    
    def generate_true_false_questions(self) -> List[Dict]:
        """Generate true/false questions"""
        pool = [
            {"text": "Python arrays are 1-indexed.", "answer": "False"},
            {"text": "HTML stands for HyperText Markup Language.", "answer": "True"},
            {"text": "A byte consists of 8 bits.", "answer": "True"},
            {"text": "Java and JavaScript are the same language.", "answer": "False"},
            {"text": "SQL is used for database management.", "answer": "True"},
            {"text": "CSS stands for Computer Style Sheets.", "answer": "False"},
            {"text": "Python is a compiled language.", "answer": "False"},
            {"text": "HTTP stands for HyperText Transfer Protocol.", "answer": "True"},
            {"text": "1 GB equals 1000 MB.", "answer": "False"},  # Actually 1024
            {"text": "The Internet and the World Wide Web are the same thing.", "answer": "False"},
            {"text": "RAM is volatile memory.", "answer": "True"},
            {"text": "0 is considered False in Python.", "answer": "True"}
        ]
        # Return 10 random questions
        return random.sample(pool, min(10, len(pool)))
    
    def generate_syntax_puzzles(self) -> List[Dict]:
        """Generate code syntax puzzles"""
        pool = [
            {"code": "print('Hello ' + ____)", "answer": "world", "hint": "Common greeting suffix"},
            {"code": "if x ____ 10:\n  print('Ten')", "answer": "==", "hint": "Equality operator"},
            {"code": "def my_func(___):\n  return x", "answer": "x", "hint": "Function argument"},
            {"code": "lst = [1, 2, 3]\nprint(lst[___])", "answer": "0", "hint": "First index"},
            {"code": "import ____ as pd", "answer": "pandas", "hint": "Data Science Library"},
            {"code": "for i in ______(5):\n  print(i)", "answer": "range", "hint": "Loop function"},
            {"code": "my_dict = {'key': ____}", "answer": "value", "hint": "Dictionary pair"},
            {"code": "class MyClass:\n  def ______(self):\n    pass", "answer": "__init__", "hint": "Constructor method"},
            {"code": "with ____ as f:\n  content = f.read()", "answer": "open", "hint": "File handling"},
            {"code": "result = 10 ____ 2", "answer": "/", "hint": "Division operator"}
        ]
        # Return 5 random puzzles
        return random.sample(pool, min(5, len(pool)))
    

    
    async def complete_round(self):
        """Handle round completion"""
        print(f"Round {self.current_round} complete for session {self.session_code}")
        
        # Cancel any running timer
        if self.round_timer_task:
            self.round_timer_task.cancel()
            self.round_timer_task = None
        
        # FIRST: Calculate who qualified and who got eliminated
        await self.calculate_and_broadcast_results()
        
        # Wait to show results
        await asyncio.sleep(3)
        
        # Check if game should continue
        # Continue if rounds remain AND (more than 1 player OR test mode)
        should_continue = self.current_round < self.total_rounds
        has_players = len(self.active_players) > 1 or (len(self.active_players) > 0 and self.is_test_mode)
        
        if should_continue and has_players:
            # Broadcast intermission before next round
            await self.manager.broadcast({
                "type": "INTERMISSION",
                "round_completed": self.current_round,
                "next_round": self.current_round + 1,
                "active_players": len(self.active_players),
                "message": f"Round {self.current_round} Complete! Preparing next round..."
            }, self.session_code)
            
            await asyncio.sleep(3)
            self.current_round += 1
            await self.start_round()
        else:
            await self.end_session()
    
    async def end_session(self):
        """End the game session"""
        print(f"Game session {self.session_code} ended")
        
        # Determine winner (player with highest score or last remaining)
        winner = self.active_players[0] if self.active_players else None
        
        await self.manager.broadcast({
            "type": "GAME_SESSION_END",
            "winner": winner,
            "final_rankings": self.active_players + self.eliminated_players,
            "message": "Game Over! Returning to lobby..."
        }, self.session_code)
        
        # Wait before redirecting
        await asyncio.sleep(5)
        
        # Redirect to lobby
        await self.manager.broadcast({
            "type": "REDIRECT_TO_LOBBY"
        }, self.session_code)


class GameSessionService:
    """Service to manage all game sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.background_tasks = set()
    
    async def start_session(self, session_code: str, players: List[Dict], manager, is_test_mode: bool = False) -> GameSession:
        """Start a new game session"""
        session = GameSession(session_code, players, manager, is_test_mode)
        self.sessions[session_code] = session
        
        # Run the start sequence in background to return session immediately
        # Store strong reference to prevent GC
        task = asyncio.create_task(self._run_start_sequence(session, session_code, manager))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        return session

    async def _run_start_sequence(self, session, session_code, manager):
        """Handle the delayed start sequence"""
        print(f"🚀 _run_start_sequence initiated for {session_code}")
        try:
            # First, redirect all players to the game page
            print(f"📡 Broadcasting GAME_START to {session_code}...")
            await manager.broadcast({
                "type": "GAME_START",
                "session_code": session_code,
                "message": "Game is starting! Redirecting to game..."
            }, session_code)
            
            # Wait for clients to redirect and reconnect WebSocket (increased from 1s to 3s to fix race condition)
            print("⏳ Waiting 3s for client redirect/reconnect...")
            await asyncio.sleep(3)
            
            # Then start the first round (which will broadcast ROUND_START)
            print("▶️ Calling session.start_round()...")
            await session.start_round()
            print(f"✓ Start sequence completed for {session_code}")
        except Exception as e:
            msg = f"CRITICAL BACKEND ERROR: {str(e)}"
            print(f"❌ {msg}")
            import traceback
            traceback.print_exc()
            
            # Broadcast error to all clients so we can see it in console
            try:
                await manager.broadcast({
                    "type": "ERROR",
                    "message": msg,
                    "details": traceback.format_exc()
                }, session_code)
            except:
                print("Failed to broadcast error message")
    
    def get_session(self, session_code: str) -> GameSession | None:
        """Get an active game session"""
        return self.sessions.get(session_code)
    
    async def complete_round(self, session_code: str):
        """Mark a round as complete and move to next"""
        session = self.sessions.get(session_code)
        if session:
            await session.complete_round()
    
    def end_session(self, session_code: str):
        """Remove a session"""
        if session_code in self.sessions:
            del self.sessions[session_code]


# Global instance
game_session_service = GameSessionService()
