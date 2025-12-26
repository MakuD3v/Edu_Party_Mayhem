from .base_game import BaseGame
from typing import List, Dict, Any
import random

class TechSprint(BaseGame):
    def __init__(self):
        self.questions = []
        self.scores = {} # player_id -> progress (0-10)

    def get_game_name(self) -> str:
        return "Tech Sprint"

    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        pool = [
            {"text": "Which isn't a programming language?", "options": ["Java", "Python", "HTML", "C++"], "answer": "HTML"},
            {"text": "What does CPU stand for?", "options": ["Central Processing Unit", "Computer Personal Unit", "Central Process Utility", "Core Processing Unit"], "answer": "Central Processing Unit"},
            {"text": "RAM is...", "options": ["Permanent Storage", "Volatile Memory", "Read Access Mode", "Remote Access Memory"], "answer": "Volatile Memory"},
            {"text": "Short for Binary Digit", "options": ["Bid", "Bit", "Byte", "Bin"], "answer": "Bit"},
            {"text": "Protocol for web browsing", "options": ["FTP", "SMTP", "HTTP", "SSH"], "answer": "HTTP"},
            {"text": "Language for database queries", "options": ["SQL", "NoSQL", "DBL", "Query++"], "answer": "SQL"},
            {"text": "Primary color of the Python logo", "options": ["Red/Green", "Blue/Yellow", "Black/White", "Purple/Orange"], "answer": "Blue/Yellow"},
            {"text": "Which is a loop?", "options": ["if", "for", "def", "class"], "answer": "for"}
        ]
        
        self.questions = []
        for _ in range(5): # Repeat pool to ensure race never runs out of questions
            random.shuffle(pool)
            self.questions.extend(pool)
            
        self.scores = {p.get('user_id', p.get('id')): 0 for p in players}
        
        return {
            "game_type": "tech_sprint",
            "game_title": "TECH SPRINT",
            "game_icon": "🚀",
            "mode": "race",  # Race game: first N to reach win_score qualify
            "win_score": 10,  # First to 10 wins
            "tutorial": {
                "text": "Race to the finish line!",
                "rules": ["Correct = Move +1", "Wrong = Move -1", "First to 10 wins!"]
            },
            "questions": self.questions
        }

    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        q_idx = action.get('question_index')
        answer = action.get('answer')
        
        current_progress = self.scores.get(player_id, 0)
        
        if 0 <= q_idx < len(self.questions):
             correct = self.questions[q_idx]['answer']
             if answer == correct:
                 current_progress = min(current_progress + 1, 10)
                 self.scores[player_id] = current_progress
                 
                 if current_progress >= 10:
                     return {"result": "correct", "score": current_progress, "win": True}
                 return {"result": "correct", "score": current_progress}
             else:
                 current_progress = max(current_progress - 1, 0)
                 self.scores[player_id] = current_progress
                 return {"result": "incorrect", "score": current_progress}
        
        # Fallback
        self.scores[player_id] = current_progress
        return {"result": "ok", "score": current_progress}

    def end(self) -> Dict[str, Any]:
        return {"scores": self.scores}

    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        pass
