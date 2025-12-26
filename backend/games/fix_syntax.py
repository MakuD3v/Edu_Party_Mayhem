from .base_game import BaseGame
from typing import List, Dict, Any
import random

class FixSyntax(BaseGame):
    def __init__(self):
        self.puzzles = []
        self.scores = {}

    def get_game_name(self) -> str:
        return "Fix The Syntax"

    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        pool = [
            {"code": "print('Hello ' + ____)", "answer": "world", "hint": "Typical greeting"},
            {"code": "if x ____ 10:\n  print('Ten')", "answer": "==", "hint": "Equality operator"},
            {"code": "def my_func(___):\n  return x", "answer": "x", "hint": "Function argument"},
            {"code": "lst = [1, 2, 3]\nprint(lst[___])", "answer": "0", "hint": "First index"},
            {"code": "import ____ as pd", "answer": "pandas", "hint": "Data Science Lib"},
            {"code": "for i in ____(5):", "answer": "range", "hint": "Loop sequence generator"},
            {"code": "dict = {'key': ____}", "answer": "value", "hint": "Key-Pair"}
        ]
        # Random sample with plenty of items
        self.puzzles = []
        for _ in range(3):
            random.shuffle(pool)
            self.puzzles.extend(pool)
            
        self.scores = {p.get('user_id', p.get('id')): 0 for p in players}
        
        return {
            "game_type": "fix_syntax",
            "game_title": "FIX THE SYNTAX",
            "game_icon": "🔧",
            "mode": "timed",  # Timed game: rank by score, use submission time as tie-breaker
            "time_limit": 30, # 30 Seconds
            "tutorial": {
                "text": "Fill in the missing code!",
                "rules": ["30 Second Timer", "Type the missing part", "Exact match required"]
            },
            "questions": self.puzzles
        }

    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        q_idx = action.get('question_index')
        user_input = action.get('answer', '').strip()
        
        if 0 <= q_idx < len(self.puzzles):
             correct = self.puzzles[q_idx]['answer']
             if user_input == correct:
                 self.scores[player_id] = self.scores.get(player_id, 0) + 1
                 return {"result": "correct", "score": self.scores[player_id]}
        
        return {"result": "incorrect"}

    def end(self) -> Dict[str, Any]:
        return {"scores": self.scores}

    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        pass
