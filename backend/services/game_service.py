from typing import Dict, Any, List
import random
from backend.games import GAME_REGISTRY
from backend.models import Session, SessionPlayer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

class GameService:
    def __init__(self):
        self.active_games: Dict[str, Any] = {} # session_code -> game_instance

    def get_active_game(self, session_code: str):
        return self.active_games.get(session_code)

    def start_round(self, session: Session, round_number: int, used_games: List[str]):
        # Select a game that hasn't been played
        available_games = [g for g in GAME_REGISTRY if g().get_game_name() not in used_games]
        if not available_games:
            available_games = GAME_REGISTRY # fallback
        
        GameClass = random.choice(available_games)
        game_instance = GameClass()
        self.active_games[session.session_code] = game_instance
        
        # Get active players
        players = [{"id": p.user_id} for p in session.players if not p.is_eliminated]
        
        start_payload = game_instance.start(players)
        return start_payload, game_instance.get_game_name()

    def handle_action(self, session_code: str, player_id: int, action: Dict[str, Any]):
        game = self.active_games.get(session_code)
        if not game:
            return {"error": "No active game"}
        return game.process_action(player_id, action)

    def end_round(self, session_code: str, round_number: int):
        game = self.active_games.get(session_code)
        if not game:
            return None
        
        results = game.end()
        del self.active_games[session_code]
        return results

    async def apply_elimination(self, db: AsyncSession, session: Session, round_number: int, game_results: Dict[str, Any]):
        # Logic for culling 50%
        # Sort players by score
        scores = game_results.get("scores", {})
        active_players = [p for p in session.players if not p.is_eliminated]
        
        # Sort desc by score
        sorted_players = sorted(active_players, key=lambda p: scores.get(p.user_id, 0), reverse=True)
        
        total = len(sorted_players)
        if round_number < 3:
            cutoff = total // 2
            # Eliminate bottom half
            eliminated = sorted_players[cutoff:]
            for p in eliminated:
                p.is_eliminated = True
            
            await db.commit()
            return {"eliminated_count": len(eliminated), "remaining_count": len(sorted_players) - len(eliminated)}
        else:
            # Final ranking
            return {"rankings": [{"user_id": p.user_id, "score": scores.get(p.user_id, 0)} for p in sorted_players]}

game_service = GameService()
