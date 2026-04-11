# tests/unit/test_notifier.py
import pytest
import os
from abc import ABC
from typing import Optional
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

class TestConcreteNotifier(Notifier):
    """Concrete implementation for testing abstract methods"""
    def send(self, alert, img_path=None):
        return True

    def send_message(self, message, img_path=None):
        return True

class TestConcreteNotifierWithValidation(Notifier):
    """Concrete implementation that validates parameters for testing"""
    def send(self, alert, img_path=None):
        if not isinstance(alert, Alert):
            raise TypeError("alert must be an Alert instance")
        if img_path is not None and not os.path.exists(img_path):
            raise FileNotFoundError(f"Image file not found: {img_path}")
        return True

    def send_message(self, message, img_path=None):
        if not isinstance(message, str):
            raise TypeError("message must be a string")
        if img_path is not None and not os.path.exists(img_path):
            raise FileNotFoundError(f"Image file not found: {img_path}")
        return True

def test_concrete_notifier_works(sample_alert):
    """Test that concrete implementation works"""
    notifier = TestConcreteNotifier()
    assert notifier.send(sample_alert) is True
    assert notifier.send_message("test") is True


# Test for type validation
def test_concrete_notifier_validates_alert_type():
    """Test that concrete implementation validates alert type"""
    notifier = TestConcreteNotifierWithValidation()

    # Should work with proper Alert
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)
    assert notifier.send(alert) is True

    # Should raise TypeError with wrong type
    with pytest.raises(TypeError, match="alert must be an Alert instance"):
        notifier.send("not an alert")


def test_concrete_notifier_validates_message_type():
    """Test that concrete implementation validates message type"""
    notifier = TestConcreteNotifierWithValidation()

    # Should work with proper string
    assert notifier.send_message("valid message") is True

    # Should raise TypeError with wrong type
    with pytest.raises(TypeError, match="message must be a string"):
        notifier.send_message(123)


def test_notifier_method_signatures():
    """Test that Notifier methods have correct signatures"""
    # Check send method signature
    import inspect
    sig = inspect.signature(Notifier.send)

    # Check parameters
    params = list(sig.parameters.keys())
    assert params == ['self', 'alert', 'img_path']

    # Check parameter types from annotations
    assert sig.parameters['alert'].annotation == Alert
    assert sig.parameters['img_path'].annotation == Optional[str]
    assert sig.return_annotation == bool

    # Check send_message method signature
    sig = inspect.signature(Notifier.send_message)
    params = list(sig.parameters.keys())
    assert params == ['self', 'message', 'img_path']

    # Check parameter types from annotations
    assert sig.parameters['message'].annotation == str
    assert sig.parameters['img_path'].annotation == Optional[str]
    assert sig.return_annotation == bool


def test_improper_implementation_missing_methods():
    """Test that incomplete implementations cannot be instantiated"""

    class IncompleteNotifier(Notifier):
        """Missing send_message method"""
        def send(self, alert, img_path=None):
            return True

    # Should raise TypeError when trying to instantiate
    with pytest.raises(TypeError):
        IncompleteNotifier()

    class AnotherIncompleteNotifier(Notifier):
        """Missing send method"""
        def send_message(self, message, img_path=None):
            return True

    # Should raise TypeError when trying to instantiate
    with pytest.raises(TypeError):
        AnotherIncompleteNotifier()


# Tests for img_path parameter handling
def test_img_path_none_handling(sample_alert, tmp_path):
    """Test that implementations handle img_path=None correctly"""
    notifier = TestConcreteNotifierWithValidation()

    # Test with img_path=None for send method
    assert notifier.send(sample_alert, img_path=None) is True

    # Test with img_path=None for send_message method
    assert notifier.send_message("test message", img_path=None) is True


def test_img_path_valid_file_handling(sample_alert, tmp_path):
    """Test that implementations handle valid img_path correctly"""
    notifier = TestConcreteNotifierWithValidation()

    # Create a temporary image file for testing
    img_file = tmp_path / "test_image.png"
    img_file.write_text("fake image data")

    # Test with valid img_path for send method
    assert notifier.send(sample_alert, img_path=str(img_file)) is True

    # Test with valid img_path for send_message method
    assert notifier.send_message("test with image", img_path=str(img_file)) is True


def test_img_path_invalid_file_handling(sample_alert):
    """Test that implementations handle invalid img_path correctly"""
    notifier = TestConcreteNotifierWithValidation()

    # Test with non-existent file for send method
    with pytest.raises(FileNotFoundError, match="Image file not found"):
        notifier.send(sample_alert, img_path="/non/existent/file.png")

    # Test with non-existent file for send_message method
    with pytest.raises(FileNotFoundError, match="Image file not found"):
        notifier.send_message("test", img_path="/non/existent/file.png")


def test_img_path_empty_string_handling(sample_alert):
    """Test that implementations handle empty string img_path"""
    notifier = TestConcreteNotifierWithValidation()

    # Empty string should be treated as provided path but file doesn't exist
    with pytest.raises(FileNotFoundError, match="Image file not found"):
        notifier.send(sample_alert, img_path="")


def test_default_implementation_img_path_optional():
    """Test that default implementation doesn't require img_path"""
    notifier = TestConcreteNotifier()

    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)

    # Should work without img_path (default value)
    assert notifier.send(alert) is True

    # Should work with explicit None
    assert notifier.send(alert, img_path=None) is True

    # Should work with message without img_path
    assert notifier.send_message("test") is True

    # Should work with message with explicit None
    assert notifier.send_message("test", img_path=None) is True


# Negative tests for improper implementations
def test_concrete_implementation_works():
    """Test that concrete implementations can be instantiated and methods work"""
    # Create a concrete implementation
    class ConcreteNotifier(Notifier):
        def send(self, alert, img_path=None):
            return True
        def send_message(self, message, img_path=None):
            return True

    # Should be able to instantiate
    notifier = ConcreteNotifier()

    # These should work since we implemented them
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)
    assert notifier.send(alert) is True
    assert notifier.send_message("test") is True

    # Verify it's a proper subclass
    assert issubclass(ConcreteNotifier, Notifier)


def test_implementation_with_wrong_return_type():
    """Test that implementations with wrong return type can still be instantiated
    (Python doesn't enforce return type annotations at runtime)"""

    class WrongReturnNotifier(Notifier):
        def send(self, alert, img_path=None):
            return "not a bool"  # Wrong return type

        def send_message(self, message, img_path=None):
            return 123  # Wrong return type

    # Python allows instantiation despite wrong return types
    notifier = WrongReturnNotifier()
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)

    # The methods will return wrong types but won't fail at instantiation
    result = notifier.send(alert)
    assert result == "not a bool"  # Not a bool as per interface

    result = notifier.send_message("test")
    assert result == 123  # Not a bool as per interface


def test_implementation_with_wrong_parameter_names():
    """Test that implementations with wrong parameter names can still be instantiated
    but may cause issues"""

    class WrongParamNotifier(Notifier):
        def send(self, wrong_param, img_path=None):  # Wrong parameter name
            return True

        def send_message(self, wrong_param, img_path=None):  # Wrong parameter name
            return True

    # Python allows instantiation
    notifier = WrongParamNotifier()
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)

    # This will work but is semantically wrong
    assert notifier.send(alert) is True
    assert notifier.send_message("test") is True


def test_abstract_class_instantiation_fails():
    """Test that abstract base class cannot be instantiated directly"""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        Notifier()


def test_subclasshook_behavior():
    """Test that subclasses are recognized correctly"""

    class ValidSubclass(Notifier):
        def send(self, alert, img_path=None):
            return True

        def send_message(self, message, img_path=None):
            return True

    class InvalidSubclass:
        """Not a real subclass - doesn't inherit from Notifier"""
        def send(self, alert, img_path=None):
            return True

        def send_message(self, message, img_path=None):
            return True

    # Valid subclass should be recognized
    assert issubclass(ValidSubclass, Notifier)

    # Invalid subclass should not be recognized
    assert not issubclass(InvalidSubclass, Notifier)

    # ABC itself should be recognized as subclass of ABC
    assert issubclass(Notifier, ABC)