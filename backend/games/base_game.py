from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseGame(ABC):
    @abstractmethod
    def get_game_name(self) -> str:
        """Returns the specific name of the game."""
        pass

    @abstractmethod
    def start(self, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Initializes the game state and returns the start payload."""
        pass

    @abstractmethod
    def process_action(self, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a player's action and returns the result."""
        pass

    @abstractmethod
    def end(self) -> Dict[str, Any]:
        """Returns the final results of the game."""
        pass
    
    @abstractmethod
    def calculate_results(self, session_players: List[Any]) -> List[Any]:
        """Calculates elimination logic or ranking."""
        pass
