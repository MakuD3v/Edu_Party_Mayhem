from .base_game import BaseGame
from typing import List, Dict, Any
import random

class TrueFalse(BaseGame):
    def __init__(self):
        self.questions = []
        self.scores = {}

    def get_game_name(self) -> str:
        return "True or False"

    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        pool = [
            {"text": "Python arrays are 1-indexed.", "answer": "False"},
            {"text": "HTML stands for HyperText Markup Language.", "answer": "True"},
            {"text": "A byte consists of 8 bits.", "answer": "True"},
            {"text": "Java and JavaScript are the same language.", "answer": "False"},
            {"text": "SQL is used for database management.", "answer": "True"},
            {"text": "Linux is an open-source OS.", "answer": "True"},
            {"text": "RAM stores data permanently.", "answer": "False"},
            {"text": "CSS is used for styling web pages.", "answer": "True"}
        ]
        
        # Pick random questions, allowing repeats if needed for length
        self.questions = [random.choice(pool) for _ in range(30)]
        self.scores = {p.get('user_id', p.get('id')): 0 for p in players}
        
        return {
            "game_type": "true_false",
            "game_title": "TRUE OR FALSE",
            "game_icon": "✅",
            "mode": "race",  # Race game: first N to reach win_score qualify
            "win_score": 10, # Answer 10 correctly to win
            "tutorial": {
                "text": "Decide if the statement is True or False.",
                "rules": ["Correct = +1 Point", "Wrong = 0 Points", "Answer 10 to win!"]
            },
            "questions": [
                {"text": q["text"], "options": ["True", "False"], "answer": q["answer"]} 
                for q in self.questions
            ]
        }

    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        q_idx = action.get('question_index')
        answer = action.get('answer') # "True" or "False"
        
        if 0 <= q_idx < len(self.questions):
             correct = self.questions[q_idx]['answer']
             if answer == correct:
                 self.scores[player_id] = self.scores.get(player_id, 0) + 1
                 score = self.scores[player_id]
                 if score >= 10:
                      return {"result": "correct", "score": score, "win": True}
                 return {"result": "correct", "score": score}
        
        return {"result": "incorrect", "score": self.scores.get(player_id, 0)}

    def end(self) -> Dict[str, Any]:
        return {"scores": self.scores}

    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        pass
