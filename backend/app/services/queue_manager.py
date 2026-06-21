import abc
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseQueueManager(abc.ABC):
    @abc.abstractmethod
    async def push_job(self, image_id: str) -> None:
        """Push an image ID to the queue for processing."""
        pass

    @abc.abstractmethod
    async def get_job(self) -> str:
        """Fetch the next image ID from the queue."""
        pass

    @abc.abstractmethod
    def task_done(self) -> None:
        """Signal that a queued task is done."""
        pass

class AsyncQueueManager(BaseQueueManager):
    """
    In-memory asyncio.Queue implementation for local lightweight background processing.
    """
    def __init__(self):
        self._queue = asyncio.Queue()

    async def push_job(self, image_id: str) -> None:
        logger.info(f"[QueueManager] Enqueueing image_id={image_id}")
        await self._queue.put(image_id)

    async def get_job(self) -> str:
        image_id = await self._queue.get()
        logger.info(f"[QueueManager] Dequeueing image_id={image_id}")
        return image_id

    def task_done(self) -> None:
        self._queue.task_done()

# Create singleton instance of QueueManager
queue_manager = AsyncQueueManager()
