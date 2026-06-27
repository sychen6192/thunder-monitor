from infrastructure.notification_manager import NotificationManager
from infrastructure.notifier import Notifier


class OkA(Notifier):
    def send_message(self, message, img_path=None): return True


class OkB(Notifier):
    def send_message(self, message, img_path=None): return True


class FailFirst(Notifier):
    def __init__(self): self.calls = 0
    def send_message(self, message, img_path=None):
        self.calls += 1
        return self.calls > 1


class AlwaysFail(Notifier):
    def __init__(self): self.calls = 0
    def send_message(self, message, img_path=None):
        self.calls += 1
        return False


class Boom(Notifier):
    def send_message(self, message, img_path=None): raise RuntimeError("boom")


def test_send_message_all_reports_each_notifier():
    manager = NotificationManager([OkA(), OkB()])
    assert manager.send_message_all("hi") == {"OkA": True, "OkB": True}


def test_retry_then_success():
    notifier = FailFirst()
    manager = NotificationManager([notifier], max_retries=1)
    assert manager.send_message_all("hi") == {"FailFirst": True}
    assert notifier.calls == 2


def test_all_attempts_fail():
    notifier = AlwaysFail()
    manager = NotificationManager([notifier], max_retries=1)
    assert manager.send_message_all("hi") == {"AlwaysFail": False}
    assert notifier.calls == 2


def test_one_failure_does_not_block_others():
    manager = NotificationManager([Boom(), OkA()], max_retries=0)
    assert manager.send_message_all("hi") == {"Boom": False, "OkA": True}
