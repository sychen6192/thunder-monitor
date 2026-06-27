import logging

from infrastructure.notifier import Notifier

logger = logging.getLogger(__name__)


class NotificationManager:
    """Fan a message out to every notifier, isolating per-channel failures and
    retrying each up to ``max_retries`` extra times. Returns {ClassName: ok}.
    """

    def __init__(self, notifiers: list[Notifier], max_retries: int = 1):
        self.notifiers = notifiers
        self.max_retries = max_retries

    def send_message_all(self, message: str, img_path: str | None = None) -> dict[str, bool]:
        return {
            type(n).__name__: self._send_with_retry(n, message, img_path)
            for n in self.notifiers
        }

    def _send_with_retry(self, notifier: Notifier, message: str, img_path: str | None) -> bool:
        name = type(notifier).__name__
        for attempt in range(self.max_retries + 1):
            try:
                if notifier.send_message(message, img_path):
                    return True
            except Exception as e:
                logger.error(f"{name} raised on attempt {attempt + 1}: {e}")
            if attempt < self.max_retries:
                logger.warning(f"Retrying {name} (attempt {attempt + 2})")
        logger.error(f"{name} failed after {self.max_retries + 1} attempt(s)")
        return False
