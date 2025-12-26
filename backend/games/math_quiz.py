from .base_game import BaseGame
from typing import List, Dict, Any
import random

class MathQuiz(BaseGame):
    def __init__(self):
        self.questions = []
        self.scores = {} # player_id -> score

    def get_game_name(self) -> str:
        return "Math Quiz"

    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.questions = [self._generate_question() for _ in range(50)] # Generous pool
        # Use user_id as the key, fallback to 'id' if needed
        self.scores = {p.get('user_id', p.get('id')): 0 for p in players}
        
        return {
            "game_type": "math_quiz",
            "game_title": "MATH QUIZ",
            "game_icon": "➗",
            "mode": "timed",  # Timed game: rank by score, use submission time as tie-breaker
            "time_limit": 20, # 20 seconds
            "tutorial": {
                "text": "Solve as many math problems as you can!",
                "rules": ["20 Second Time Limit", "Correct = +1 Point", "Wrong = -1 Point"]
            },
            "questions": self.questions
        }

    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        # action = { "question_index": 0, "answer": 10 }
        q_idx = action.get('question_index')
        answer = action.get('answer')
        
        if 0 <= q_idx < len(self.questions):
             correct = self.questions[q_idx]['answer']
             if int(answer) == correct:
                 self.scores[player_id] = self.scores.get(player_id, 0) + 1
                 return {"result": "correct", "score": self.scores[player_id]}
             else:
                 # Optional: Penalty for wrong answer? Plan said -1
                 self.scores[player_id] = max(0, self.scores.get(player_id, 0) - 1)
                 return {"result": "incorrect", "score": self.scores[player_id]}
        
        return {"result": "incorrect"}

    def end(self) -> Dict[str, Any]:
        return {"scores": self.scores}

    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        # Sort players by score
        pass

    def _generate_question(self):
        a = random.randint(1, 12)
        b = random.randint(1, 12)
        op = random.choice(['+', '-', '*'])
        if op == '+': ans = a + b
        elif op == '-': ans = a - b
        else: ans = a * b
        return {"text": f"{a} {op} {b}", "answer": ans}
