# infrastructure/notifier.py
from abc import ABC, abstractmethod
from typing import Optional
from models.alert import Alert

class Notifier(ABC):
    """Abstract base class for notification providers"""

    @abstractmethod
    def send(self, alert: Alert, img_path: Optional[str] = None) -> bool:
        """
        Send alert notification.

        Args:
            alert: Alert object to send
            img_path: Optional path to image file

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def send_message(self, message: str, img_path: Optional[str] = None) -> bool:
        """
        Send simple text message.

        Args:
            message: Text message to send
            img_path: Optional path to image file

        Returns:
            bool: True if successful, False otherwise
        """
        pass