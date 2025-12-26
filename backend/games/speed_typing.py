from .base_game import BaseGame
from typing import List, Dict, Any
import random

class SpeedTyping(BaseGame):
    WORDS = ["python", "java", "coding", "fastapi", "education", "party", "mayhem", 
             "keyboard", "screen", "mouse", "algorithm", "database", "network", 
             "server", "client", "socket", "router", "switch", "binary", "pixel"]

    def __init__(self):
        self.word_list = []
        self.scores = {}

    def get_game_name(self) -> str:
        return "Speed Typing"

    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Generate a long list of random words for streaming
        self.word_list = [random.choice(self.WORDS) for _ in range(50)]
        self.scores = {p.get('user_id', p.get('id')): 0 for p in players}
        
        return {
            "game_type": "speed_typing",
            "game_title": "SPEED TYPING",
            "game_icon": "⌨️",
            "mode": "timed",  # Timed game: rank by score, use submission time as tie-breaker
            "time_limit": 20, # 20 seconds
            "tutorial": {
                "text": "Type the words as fast as you can!",
                "rules": ["20 Second Time Limit", "Type exactly what you see", "Speed is key!"]
            },
            "word_list": self.word_list
        }

    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        word_index = action.get('word_index')
        typed_word = action.get('word')
        
        if 0 <= word_index < len(self.word_list):
            target = self.word_list[word_index]
            if typed_word == target:
                self.scores[player_id] = self.scores.get(player_id, 0) + 1
                return {"result": "correct", "score": self.scores[player_id]}
                
        return {"result": "incorrect"}

    def end(self) -> Dict[str, Any]:
        return {"scores": self.scores}

    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        pass
