from .base_game import BaseGame
from .math_quiz import MathQuiz
from .speed_typing import SpeedTyping
from .tech_sprint import TechSprint
from .true_false import TrueFalse
from .fix_syntax import FixSyntax

GAME_REGISTRY = []

def register_game(game_class):
    GAME_REGISTRY.append(game_class)

# Auto-register games
register_game(MathQuiz)
register_game(SpeedTyping)
register_game(TechSprint)
register_game(TrueFalse)
register_game(FixSyntax)
