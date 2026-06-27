# infrastructure/notifier.py
from abc import ABC, abstractmethod
from typing import Optional


class Notifier(ABC):
    """Contract for notification providers.

    Implementations return True on successful delivery and False on failure,
    so callers (e.g. NotificationManager) can fan out and retry.
    """

    @abstractmethod
    def send_message(self, message: str, img_path: Optional[str] = None) -> bool:
        """Send a message, optionally with an image."""
        ...
