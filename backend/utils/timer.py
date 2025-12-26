import asyncio
from typing import Callable, Optional

class GameTimer:
    def __init__(self, duration: int, on_tick: Optional[Callable[[int], None]] = None, on_finish: Optional[Callable[[], None]] = None):
        self.duration = duration
        self.remaining = duration
        self.on_tick = on_tick
        self.on_finish = on_finish
        self.task: Optional[asyncio.Task] = None
        self._cancelled = False

    async def start(self):
        self._cancelled = False
        self.remaining = self.duration
        self.task = asyncio.create_task(self._run())

    async def _run(self):
        while self.remaining > 0 and not self._cancelled:
            if self.on_tick:
                if asyncio.iscoroutinefunction(self.on_tick):
                    await self.on_tick(self.remaining)
                else:
                    self.on_tick(self.remaining)
            await asyncio.sleep(1)
            self.remaining -= 1
        
        if not self._cancelled and self.on_finish:
             if asyncio.iscoroutinefunction(self.on_finish):
                await self.on_finish()
             else:
                self.on_finish()

    def stop(self):
        self._cancelled = True
        if self.task:
            self.task.cancel()
