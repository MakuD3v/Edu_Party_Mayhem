from typing import List
from backend.models import Session
from backend.services.inactivity_service import InactivityService

class LobbyService:
    def __init__(self):
        self.inactivity_monitor = InactivityService()

    async def register_session_activity(self, session_code: str):
        self.inactivity_monitor.update_activity(session_code)

    async def start_tracking(self, session_code: str, on_timeout):
        await self.inactivity_monitor.start_monitoring(session_code, on_timeout)

    async def stop_tracking(self, session_code: str):
        self.inactivity_monitor.stop_monitoring(session_code)

lobby_service = LobbyService()
