import logging
from typing import Callable

from models.alert import Alert
from infrastructure.notifier import Notifier

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self, notifiers: list[Notifier], max_retries: int = 1):
        self.notifiers = notifiers
        self.max_retries = max_retries

    def send_all(self, alert: Alert, img_path: str | None = None) -> dict[str, bool]:
        return self._dispatch(lambda n: n.send(alert, img_path))

    def send_message_all(self, message: str, img_path: str | None = None) -> dict[str, bool]:
        return self._dispatch(lambda n: n.send_message(message, img_path))

    def _dispatch(self, action: Callable[[Notifier], bool]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for notifier in self.notifiers:
            name = type(notifier).__name__
            results[name] = self._with_retry(name, action, notifier)
        return results

    def _with_retry(self, name: str, action: Callable[[Notifier], bool], notifier: Notifier) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                if action(notifier):
                    return True
            except Exception as e:
                logger.error(f"{name} raised on attempt {attempt + 1}: {e}")
            if attempt < self.max_retries:
                logger.warning(f"Retrying {name} (attempt {attempt + 2})")
        logger.error(f"{name} failed after {self.max_retries + 1} attempt(s)")
        return False
