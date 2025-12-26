import asyncio
from typing import Dict, Any
from backend.utils.timer import GameTimer

class InactivityService:
    def __init__(self):
        self._timers: Dict[str, GameTimer] = {}

    async def start_monitoring(self, session_code: str, callback):
        # 10 minutes = 600 seconds
        timer = GameTimer(600, on_finish=lambda: asyncio.create_task(callback(session_code)))
        self._timers[session_code] = timer
        await timer.start()

    def update_activity(self, session_code: str):
        if session_code in self._timers:
            # Restart timer
            asyncio.create_task(self._timers[session_code].start())

    def stop_monitoring(self, session_code: str):
        if session_code in self._timers:
            self._timers[session_code].stop()
            del self._timers[session_code]
