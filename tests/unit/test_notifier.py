# tests/unit/test_notifier.py
import pytest
from abc import ABC
from infrastructure.notifier import Notifier
from models.alert import Alert

def test_notifier_is_abstract():
    """Verify Notifier is an abstract class"""
    assert issubclass(Notifier, ABC)

    # Should not be instantiable
    with pytest.raises(TypeError):
        Notifier()

def test_notifier_has_required_methods():
    """Verify Notifier has required abstract methods"""
    assert hasattr(Notifier, 'send')
    assert hasattr(Notifier, 'send_message')

    # Check methods are abstract
    assert Notifier.send.__isabstractmethod__
    assert Notifier.send_message.__isabstractmethod__

class TestNotifier(Notifier):
    """Concrete implementation for testing"""
    def send(self, alert, img_path=None):
        return True

    def send_message(self, message, img_path=None):
        return True

def test_concrete_notifier_works(sample_alert):
    """Test that concrete implementation works"""
    notifier = TestNotifier()
    assert notifier.send(sample_alert) is True
    assert notifier.send_message("test") is True