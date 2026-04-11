# infrastructure/notifier.py
from abc import ABC, abstractmethod
from typing import Optional
from models.alert import Alert

class Notifier(ABC):
    """Abstract base class for notification providers.

    This interface defines the contract for all notification implementations.
    Concrete implementations must handle sending notifications with optional images.

    Error Handling Contract:
        - Implementations should return True on successful notification delivery
        - Implementations should return False on failure (e.g., network issues, invalid parameters)
        - Implementations should raise appropriate exceptions for unrecoverable errors
        - Callers should handle False returns as expected failures (e.g., retry logic)

    Image Handling:
        - img_path parameter is optional and can be None
        - When img_path is provided, implementations should validate the file exists and is accessible
        - Implementations should handle unsupported image formats gracefully
        - Implementations may choose to send notification without image if image processing fails

    Example Usage:
        >>> class MyNotifier(Notifier):
        ...     def send(self, alert: Alert, img_path: Optional[str] = None) -> bool:
        ...         # Implementation logic here
        ...         return True
        ...
        ...     def send_message(self, message: str, img_path: Optional[str] = None) -> bool:
        ...         # Implementation logic here
        ...         return True
    """

    @abstractmethod
    def send(self, alert: Alert, img_path: Optional[str] = None) -> bool:
        """
        Send alert notification.

        Args:
            alert: Alert object to send. Must be a valid Alert instance.
            img_path: Optional path to image file. Can be None or a string path.

        Returns:
            bool: True if notification was successfully sent, False otherwise.

        Raises:
            TypeError: If alert is not an Alert instance
            FileNotFoundError: If img_path is provided but file doesn't exist (optional)
            ValueError: If alert contains invalid data (optional)
        """
        pass

    @abstractmethod
    def send_message(self, message: str, img_path: Optional[str] = None) -> bool:
        """
        Send simple text message.

        Args:
            message: Text message to send. Must be a non-empty string.
            img_path: Optional path to image file. Can be None or a string path.

        Returns:
            bool: True if notification was successfully sent, False otherwise.

        Raises:
            TypeError: If message is not a string
            ValueError: If message is empty (optional)
            FileNotFoundError: If img_path is provided but file doesn't exist (optional)
        """
        pass