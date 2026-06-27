# tests/unit/test_notifier.py
import inspect
from abc import ABC
from typing import Optional

import pytest

from infrastructure.notifier import Notifier


def test_notifier_is_abstract_and_uninstantiable():
    assert issubclass(Notifier, ABC)
    with pytest.raises(TypeError):
        Notifier()


def test_send_message_is_the_abstract_contract():
    assert Notifier.send_message.__isabstractmethod__


def test_concrete_subclass_implementing_send_message_works():
    class Ok(Notifier):
        def send_message(self, message, img_path=None):
            return True

    notifier = Ok()
    assert notifier.send_message("hi") is True
    assert notifier.send_message("hi", img_path=None) is True


def test_subclass_missing_send_message_cannot_instantiate():
    class Incomplete(Notifier):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_send_message_signature():
    sig = inspect.signature(Notifier.send_message)
    assert list(sig.parameters) == ["self", "message", "img_path"]
    assert sig.parameters["message"].annotation == str
    assert sig.parameters["img_path"].annotation == Optional[str]
    assert sig.return_annotation == bool
