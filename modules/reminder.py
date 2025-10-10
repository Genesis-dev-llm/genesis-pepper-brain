# modules/reminder.py
from core.logger import logger
import asyncio
from typing import TYPE_CHECKING, Optional, Coroutine, Any, Callable


if TYPE_CHECKING: 
    from modules.task_manager import TaskManager
    from modules.pepper_interface import PepperInterface


class ReminderService: 
    def __init__(self, task_manager: 'TaskManager', pepper_interface: 'PepperInterface'):
        self.task_manager = task_manager
        self.pepper_interface = pepper_interface
        logger.info("ReminderService initialized with PepperInterface.")


    def setup_reminder(self, message: str, time_str: str, reminder_name: Optional[str] = None) -> str: 
        """
        Sets up a daily reminder using the TaskManager.
        :param message: The message to be spoken by Pepper.
        :param time_str: The time for the reminder in "HH:MM" format.
        :return: Confirmation or error message string.
        """
        if not reminder_name:
            reminder_name = f"daily_reminder_{time_str.replace(':', '')}_{message[:10].replace(' ','_')}"
        
        # Action is now the Pepper-specific speak method
        return self.task_manager.add_task(
            name=reminder_name,
            description=f"Speak reminder via Pepper: {message}",
            schedule_time=time_str, 
            action=self._speak_reminder_action, 
            action_args=(message,) 
        )


    async def _speak_reminder_action(self, message: str) -> None:
        """
        The actual action performed by the TaskManager when a reminder is due.
        Uses the PepperInterface to deliver the message.
        """
        logger.info(f"Executing Reminder: {message}")
        try:
            # Use the async speak method from the Pepper Interface
            await self.pepper_interface.speak_async(f"Reminder: {message}")
            logger.info(f"Reminder '{message}' spoken via Pepper successfully.")
        except Exception as e:
            logger.error(f"Error during reminder speak action via Pepper for message '{message}': {e}", exc_info=True)


    def cancel_reminder(self, reminder_name: str) -> str:
        """Cancels a reminder task by its name."""
        return self.task_manager.remove_task(reminder_name)