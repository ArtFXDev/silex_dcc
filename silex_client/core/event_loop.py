from threading import Thread
from typing import Coroutine
import asyncio
from contextlib import suppress

from silex_client.utils.log import logger

class EventLoop:
    """
    Class responsible to manage the async event loop, to deal with websocket
    connection, and action execution
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.tasks = []
        self.thread = None

    def _start_event_loop(self) -> None:
        self.pending_stop = False
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

        # Stop the event loop and clear it once completed
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._clear_event_loop()

    def _clear_event_loop(self) -> None:
        if self.loop.is_running():
            logger.info("Could not clear the event loop: The loop must be stopped before being cleared")
            return

        logger.info("Clearing event loop...")
        # Clear the loop
        for task in asyncio.all_tasks(self.loop):
            # The cancel method will raise CancelledError on the running task to stop it
            task.cancel()
            # Wait for the task's cancellation in a suppress context to mute the CancelledError
            with suppress(asyncio.CancelledError):
                self.loop.run_until_complete(task)

    def start(self) -> None:
        """
        initialize the event loop's task and run it in main thread
        """
        if self.loop.is_running():
            logger.warning("Could not start event loop: The loop is already running")
            return

        self._start_event_loop()

    def start_multithreaded(self) -> None:
        """
        initialize the event loop's task and run it in a different thread
        """
        if self.loop.is_running():
            logger.warning("Could not start event loop: The loop is already running")
            return

        self.thread = Thread(target=self._start_event_loop)
        self.thread.start()

    def stop(self) -> None:
        """
        Ask to all the event loop's tasks to stop and join the thread to the main thread
        if there is one running
        """
        if self.loop.is_running():
            logger.warning("Could not stop event loop: The loop is not running")
            return

        if self.thread is not None and self.thread.isAlive():
            self.loop.call_soon_threadsafe(self.loop.stop)
        else:
            self.loop.stop()

    def register_task(self, coroutine: Coroutine) -> None:
        self.loop.create_task(coroutine)
