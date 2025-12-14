"""
Event bus for broadcasting updates to frontend (SSE)
"""
import asyncio
import logging
import json
from typing import List, Any, Dict

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers: List[asyncio.Queue] = []
        self.loop: asyncio.AbstractEventLoop = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the main event loop"""
        self.loop = loop

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to events"""
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from events"""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    async def publish(self, event: Dict[str, Any]):
        """Publish an event to all subscribers"""
        # Clean up closed queues (optional, but good practice if not handled elsewhere)
        for queue in self.subscribers:
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Error putting to queue: {e}")

    def publish_sync(self, event: Dict[str, Any]):
        """Publish event from synchronous code"""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.publish(event), self.loop)
        else:
            # Fallback or warning
            # In some cases (like unit tests or script run), loop might not be set
            pass

# Global instance
event_bus = EventBus()
