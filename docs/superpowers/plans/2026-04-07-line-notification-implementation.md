# Line Notification Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Line Messaging API notifications with Imgur image support alongside existing Telegram notifications, improving code organization with Strategy Pattern.

**Architecture:** Create Notifier interface, implement LineNotifier with ImgurClient for image hosting, create NotificationManager to handle multiple notifiers, refactor AlertService to use manager.

**Tech Stack:** Python 3.11+, requests, line-bot-sdk, pyimgur, pytest, loguru

---

## Context
The Thunder Alert Monitor currently sends notifications only via Telegram. Users need dual notifications (Telegram + Line) for wider coverage. Line Messaging API requires HTTPS URLs for images, so Imgur API integration is needed for image hosting. The codebase currently has tight coupling between AlertService and TelegramNotifier, lacking abstraction and testability.

## File Structure

### New Files:
- `infrastructure/notifier.py` - Abstract Notifier interface
- `infrastructure/line_notifier.py` - Line Messaging API implementation  
- `infrastructure/imgur_client.py` - Imgur API client for image hosting
- `infrastructure/notification_manager.py` - Manages multiple notifiers
- `tests/unit/test_notifier.py` - Unit tests for notification components
- `tests/unit/test_imgur_client.py` - Unit tests for Imgur client
- `tests/integration/test_notification_flow.py` - Integration tests

### Modified Files:
- `infrastructure/telegram_notifier.py` - Update to implement Notifier interface
- `services/alert_service.py` - Refactor to use NotificationManager
- `infrastructure/config.py` - Add validation for new configs
- `config.yaml` - Add Line and Imgur configuration
- `requirements.txt` - Add line-bot-sdk and pyimgur dependencies
- `file_repo.py` - Fix bug on line 11 (join Alert objects)

## Implementation Tasks

### Task 1: Fix file_repo.py bug and setup testing

**Files:**
- Modify: `infrastructure/file_repo.py:11`
- Create: `requirements.txt` (update)
- Create: `tests/conftest.py`
- Create: `tests/unit/test_file_repo.py`

- [ ] **Step 1: Fix the bug in file_repo.py**

```python
# Current line 11 (buggy):
# ALERT_FILE.write_text("\n".join(alerts))

# Fixed line 11:
import json
ALERT_FILE.write_text("\n".join(json.dumps(alert.__dict__) for alert in alerts))
```

- [ ] **Step 2: Add testing dependencies to requirements.txt**

```txt
# Add to requirements.txt:
pytest==7.4.0
pytest-mock==3.11.1
line-bot-sdk==3.5.0
pyimgur==0.7.0
```

- [ ] **Step 3: Create conftest.py with fixtures**

```python
# tests/conftest.py
import pytest
from models.alert import Alert
from datetime import datetime

@pytest.fixture
def sample_alert():
    return Alert(
        category="Cloud-to-ground",
        occur_time="2024-01-01 12:00",
        latitude=25.0,
        longitude=121.5
    )

@pytest.fixture
def sample_alerts():
    return [
        Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5),
        Alert("Cloud-to-cloud", "2024-01-01 12:05", 25.1, 121.6)
    ]
```

- [ ] **Step 4: Write test for file_repo.py**

```python
# tests/unit/test_file_repo.py
import json
import tempfile
import os
from pathlib import Path
from models.alert import Alert
from infrastructure.file_repo import save_alerts, load_alerts, reset_alerts

def test_save_and_load_alerts(sample_alerts):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_alerts.txt"
        
        # Save alerts
        save_alerts(sample_alerts)
        
        # Load alerts
        loaded = load_alerts()
        
        assert len(loaded) == len(sample_alerts)
        assert loaded[0].category == sample_alerts[0].category
        assert loaded[0].latitude == sample_alerts[0].latitude

def test_reset_alerts():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_alerts.txt"
        test_file.write_text("test data")
        
        reset_alerts()
        
        assert test_file.read_text() == ""
```

- [ ] **Step 5: Run test to verify fix**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_file_repo.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add infrastructure/file_repo.py requirements.txt tests/
git commit -m "fix: file_repo bug and add test infrastructure"
```

### Task 2: Create Notifier interface

**Files:**
- Create: `infrastructure/notifier.py`
- Create: `tests/unit/test_notifier.py`

- [ ] **Step 1: Create Notifier abstract base class**

```python
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
```

- [ ] **Step 2: Write interface validation test**

```python
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
```

- [ ] **Step 3: Run interface tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_notifier.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/notifier.py tests/unit/test_notifier.py
git commit -m "feat: add Notifier abstract interface"
```

### Task 3: Update TelegramNotifier to implement Notifier

**Files:**
- Modify: `infrastructure/telegram_notifier.py`
- Create: `tests/unit/test_telegram_notifier.py`

- [ ] **Step 1: Update TelegramNotifier imports and class**

```python
# infrastructure/telegram_notifier.py
import requests
import textwrap
import logging

from models.alert import Alert
from infrastructure.utils import get_google_url
from infrastructure.notifier import Notifier

logger = logging.getLogger(__name__)

class TelegramNotifier(Notifier):  # Changed to implement Notifier
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
    
    def send(self, alert: Alert, img_path=None) -> bool:  # Added return type
        msg = textwrap.dedent(f"""\
        時間：{alert.occur_time}
        類型：{alert.category}
        經緯度：({alert.latitude}, {alert.longitude})
        {get_google_url(alert.longitude, alert.latitude)}
        """)
        return self.send_message(msg, img_path)
    
    def send_message(self, msg, img_path=None) -> bool:  # Added return type
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": msg}
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            if img_path:
                url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
                with open(img_path, "rb") as photo:
                    response = requests.post(url, data={"chat_id": self.chat_id}, files={"photo": photo})
                response.raise_for_status()
            
            return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
```

- [ ] **Step 2: Write TelegramNotifier tests**

```python
# tests/unit/test_telegram_notifier.py
import pytest
from unittest.mock import Mock, patch
from infrastructure.telegram_notifier import TelegramNotifier
from models.alert import Alert

def test_telegram_notifier_implements_notifier():
    """Verify TelegramNotifier implements Notifier interface"""
    from infrastructure.notifier import Notifier
    assert issubclass(TelegramNotifier, Notifier)

def test_send_message_success():
    """Test successful message sending"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        notifier = TelegramNotifier("fake_token", "fake_chat_id")
        result = notifier.send_message("test message")
        
        assert result is True
        mock_post.assert_called_once()

def test_send_message_failure():
    """Test failed message sending"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("API error")
        
        notifier = TelegramNotifier("fake_token", "fake_chat_id")
        result = notifier.send_message("test message")
        
        assert result is False

def test_send_alert(sample_alert):
    """Test sending alert"""
    with patch('infrastructure.telegram_notifier.TelegramNotifier.send_message') as mock_send:
        mock_send.return_value = True
        
        notifier = TelegramNotifier("fake_token", "fake_chat_id")
        result = notifier.send(sample_alert)
        
        assert result is True
        mock_send.assert_called_once()
```

- [ ] **Step 3: Run TelegramNotifier tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_telegram_notifier.py -v
```
Expected: 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/telegram_notifier.py tests/unit/test_telegram_notifier.py
git commit -m "refactor: update TelegramNotifier to implement Notifier interface"
```

### Task 4: Implement ImgurClient

**Files:**
- Create: `infrastructure/imgur_client.py`
- Create: `tests/unit/test_imgur_client.py`

- [ ] **Step 1: Create ImgurClient class**

```python
# infrastructure/imgur_client.py
import requests
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ImgurClient:
    """Client for uploading images to Imgur"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.base_url = "https://api.imgur.com/3"
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """
        Upload image to Imgur and return URL.
        
        Args:
            image_path: Path to local image file
            
        Returns:
            str: HTTPS URL of uploaded image, or None if failed
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                b64_image = base64.b64encode(image_file.read()).decode()
            
            # Prepare request
            headers = {"Authorization": f"Client-ID {self.client_id}"}
            data = {"image": b64_image, "type": "base64"}
            
            # Upload to Imgur
            response = requests.post(
                f"{self.base_url}/upload",
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            # Extract URL from response
            result = response.json()
            if result.get("success", False):
                url = result["data"]["link"]
                logger.info(f"Image uploaded to Imgur: {url}")
                return url
            else:
                logger.error(f"Imgur upload failed: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Imgur API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload to Imgur: {e}")
            return None
    
    def upload_image_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """
        Upload image from bytes to Imgur.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            str: HTTPS URL of uploaded image, or None if failed
        """
        try:
            b64_image = base64.b64encode(image_bytes).decode()
            headers = {"Authorization": f"Client-ID {self.client_id}"}
            data = {"image": b64_image, "type": "base64"}
            
            response = requests.post(
                f"{self.base_url}/upload",
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("success", False):
                return result["data"]["link"]
            else:
                logger.error(f"Imgur upload failed: {result}")
                return None
        except Exception as e:
            logger.error(f"Failed to upload bytes to Imgur: {e}")
            return None
```

- [ ] **Step 2: Write ImgurClient tests**

```python
# tests/unit/test_imgur_client.py
import pytest
from unittest.mock import Mock, patch, mock_open
from infrastructure.imgur_client import ImgurClient

def test_upload_image_success():
    """Test successful image upload"""
    with patch('builtins.open', mock_open(read_data=b'test_image_data')), \
         patch('base64.b64encode') as mock_b64, \
         patch('requests.post') as mock_post:
        
        mock_b64.return_value = b'encoded_data'
        mock_b64.return_value.decode.return_value = 'encoded_string'
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"link": "https://i.imgur.com/abc123.jpg"}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = ImgurClient("test_client_id")
        url = client.upload_image("test.jpg")
        
        assert url == "https://i.imgur.com/abc123.jpg"
        mock_post.assert_called_once()

def test_upload_image_api_failure():
    """Test Imgur API failure"""
    with patch('builtins.open', mock_open(read_data=b'test_data')), \
         patch('requests.post') as mock_post:
        
        mock_post.side_effect = Exception("API error")
        
        client = ImgurClient("test_client_id")
        url = client.upload_image("test.jpg")
        
        assert url is None

def test_upload_image_from_bytes():
    """Test uploading image from bytes"""
    with patch('base64.b64encode') as mock_b64, \
         patch('requests.post') as mock_post:
        
        mock_b64.return_value = b'encoded_data'
        mock_b64.return_value.decode.return_value = 'encoded_string'
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"link": "https://i.imgur.com/xyz789.jpg"}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = ImgurClient("test_client_id")
        url = client.upload_image_from_bytes(b'test_bytes')
        
        assert url == "https://i.imgur.com/xyz789.jpg"
```

- [ ] **Step 3: Run ImgurClient tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_imgur_client.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/imgur_client.py tests/unit/test_imgur_client.py
git commit -m "feat: add ImgurClient for image hosting"
```

### Task 5: Implement LineNotifier

**Files:**
- Create: `infrastructure/line_notifier.py`
- Create: `tests/unit/test_line_notifier.py`

- [ ] **Step 1: Create LineNotifier class**

```python
# infrastructure/line_notifier.py
import requests
import json
import logging
from typing import Optional
from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.utils import get_google_url

logger = logging.getLogger(__name__)

class LineNotifier(Notifier):
    """Line Messaging API notifier"""
    
    def __init__(
        self, 
        channel_access_token: str, 
        channel_secret: str, 
        user_id: str,
        imgur_client: Optional[ImgurClient] = None
    ):
        self.channel_access_token = channel_access_token
        self.channel_secret = channel_secret
        self.user_id = user_id
        self.imgur_client = imgur_client
        self.base_url = "https://api.line.me/v2/bot"
    
    def send(self, alert: Alert, img_path: Optional[str] = None) -> bool:
        """Send alert notification to Line with optional image"""
        message = self._format_alert_message(alert)
        return self._send_line_message(message, img_path)
    
    def send_message(self, message: str, img_path: Optional[str] = None) -> bool:
        """Send simple message to Line with optional image"""
        return self._send_line_message(message, img_path)
    
    def _format_alert_message(self, alert: Alert) -> str:
        """Format alert for Line message"""
        return f"""⚡ 雷擊警報 ⚡
時間：{alert.occur_time}
類型：{alert.category}
經緯度：({alert.latitude}, {alert.longitude})
地圖：{get_google_url(alert.longitude, alert.latitude)}"""
    
    def _send_line_message(self, text: str, img_path: Optional[str] = None) -> bool:
        """Send message to Line, optionally with image"""
        headers = {
            "Authorization": f"Bearer {self.channel_access_token}",
            "Content-Type": "application/json"
        }
        
        # Build messages array
        messages = [{"type": "text", "text": text}]
        
        # Add image if provided and Imgur client available
        if img_path and self.imgur_client:
            image_url = self.imgur_client.upload_image(img_path)
            if image_url:
                messages.append({
                    "type": "image",
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url
                })
                logger.info(f"Line message with image: {image_url}")
            else:
                logger.warning("Imgur upload failed, sending text-only to Line")
        
        payload = {
            "to": self.user_id,
            "messages": messages
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/message/push",
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Line notification sent successfully to {self.user_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Line API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Line notification failed: {e}")
            return False
```

- [ ] **Step 2: Write LineNotifier tests**

```python
# tests/unit/test_line_notifier.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from models.alert import Alert

def test_line_notifier_implements_notifier():
    """Verify LineNotifier implements Notifier interface"""
    from infrastructure.notifier import Notifier
    assert issubclass(LineNotifier, Notifier)

def test_format_alert_message(sample_alert):
    """Test alert message formatting"""
    notifier = LineNotifier("token", "secret", "user123", None)
    message = notifier._format_alert_message(sample_alert)
    
    assert "雷擊警報" in message
    assert sample_alert.occur_time in message
    assert sample_alert.category in message
    assert "https://www.google.com/maps?" in message

def test_send_message_success():
    """Test successful message sending without image"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        notifier = LineNotifier("token", "secret", "user123", None)
        result = notifier.send_message("test message")
        
        assert result is True
        mock_post.assert_called_once()

def test_send_message_with_image_success():
    """Test successful message sending with image"""
    with patch('requests.post') as mock_post, \
         patch.object(ImgurClient, 'upload_image') as mock_upload:
        
        mock_upload.return_value = "https://i.imgur.com/test.jpg"
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        imgur_client = ImgurClient("test_id")
        notifier = LineNotifier("token", "secret", "user123", imgur_client)
        result = notifier.send_message("test message", "test.jpg")
        
        assert result is True
        mock_upload.assert_called_once_with("test.jpg")
        
        # Verify both text and image messages in payload
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]['data'])
        assert len(payload['messages']) == 2
        assert payload['messages'][0]['type'] == 'text'
        assert payload['messages'][1]['type'] == 'image'

def test_send_message_with_image_fallback():
    """Test image upload failure falls back to text-only"""
    with patch('requests.post') as mock_post, \
         patch.object(ImgurClient, 'upload_image') as mock_upload:
        
        mock_upload.return_value = None  # Simulate upload failure
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        imgur_client = ImgurClient("test_id")
        notifier = LineNotifier("token", "secret", "user123", imgur_client)
        result = notifier.send_message("test message", "test.jpg")
        
        assert result is True
        mock_upload.assert_called_once_with("test.jpg")
        
        # Verify only text message in payload
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]['data'])
        assert len(payload['messages']) == 1
        assert payload['messages'][0]['type'] == 'text'

def test_send_alert(sample_alert):
    """Test sending alert"""
    with patch('infrastructure.line_notifier.LineNotifier._send_line_message') as mock_send:
        mock_send.return_value = True
        
        notifier = LineNotifier("token", "secret", "user123", None)
        result = notifier.send(sample_alert)
        
        assert result is True
        mock_send.assert_called_once()
```

- [ ] **Step 3: Run LineNotifier tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_line_notifier.py -v
```
Expected: 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/line_notifier.py tests/unit/test_line_notifier.py
git commit -m "feat: add LineNotifier with Imgur image support"
```

### Task 6: Implement NotificationManager

**Files:**
- Create: `infrastructure/notification_manager.py`
- Create: `tests/unit/test_notification_manager.py`

- [ ] **Step 1: Create NotificationManager class**

```python
# infrastructure/notification_manager.py
import logging
from typing import Dict, List, Optional
from models.alert import Alert
from infrastructure.notifier import Notifier

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages multiple notification channels"""
    
    def __init__(self, notifiers: List[Notifier], max_retries: int = 1):
        """
        Initialize NotificationManager.
        
        Args:
            notifiers: List of Notifier instances
            max_retries: Maximum retry attempts per notifier (default: 1)
        """
        self.notifiers = notifiers
        self.max_retries = max_retries
    
    def send_all(self, alert: Alert, img_path: Optional[str] = None) -> Dict[str, bool]:
        """
        Send alert to all notifiers with retry logic.
        
        Args:
            alert: Alert object to send
            img_path: Optional path to image file
            
        Returns:
            Dict[str, bool]: Success status per notifier (by class name)
        """
        results = {}
        
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            success = False
            
            for attempt in range(self.max_retries + 1):
                try:
                    success = notifier.send(alert, img_path)
                    if success:
                        logger.info(f"{notifier_name} succeeded on attempt {attempt + 1}")
                        break
                    elif attempt < self.max_retries:
                        logger.warning(f"Retrying {notifier_name}, attempt {attempt + 1}")
                except Exception as e:
                    logger.error(f"{notifier_name} failed (attempt {attempt + 1}): {e}")
                    if attempt == self.max_retries:
                        success = False
            
            results[notifier_name] = success
            if not success:
                logger.error(f"{notifier_name} failed after {self.max_retries + 1} attempts")
        
        return results
    
    def send_message_all(self, message: str, img_path: Optional[str] = None) -> Dict[str, bool]:
        """
        Send simple message to all notifiers.
        
        Args:
            message: Text message to send
            img_path: Optional path to image file
            
        Returns:
            Dict[str, bool]: Success status per notifier (by class name)
        """
        results = {}
        for notifier in self.notifiers:
            notifier_name = notifier.__class__.__name__
            try:
                results[notifier_name] = notifier.send_message(message, img_path)
                if results[notifier_name]:
                    logger.info(f"{notifier_name} message sent successfully")
                else:
                    logger.error(f"{notifier_name} message failed")
            except Exception as e:
                logger.error(f"{notifier_name} message failed: {e}")
                results[notifier_name] = False
        return results
    
    def get_notifier_status(self) -> Dict[str, str]:
        """Get status of all notifiers (for monitoring)"""
        return {
            notifier.__class__.__name__: "enabled"
            for notifier in self.notifiers
        }
```

- [ ] **Step 2: Write NotificationManager tests**

```python
# tests/unit/test_notification_manager.py
import pytest
from unittest.mock import Mock, patch
from infrastructure.notification_manager import NotificationManager
from models.alert import Alert

class MockNotifier:
    def __init__(self, name, success_on_first=True):
        self.name = name
        self.attempts = 0
        self.success_on_first = success_on_first
    
    def send(self, alert, img_path=None):
        self.attempts += 1
        if self.success_on_first or self.attempts > 1:
            return True
        return False
    
    def send_message(self, message, img_path=None):
        return True
    
    def __class__(self):
        class MockClass:
            __name__ = self.name
        return MockClass()

def test_notification_manager_send_all():
    """Test sending to multiple notifiers"""
    notifier1 = MockNotifier("TelegramNotifier", success_on_first=True)
    notifier2 = MockNotifier("LineNotifier", success_on_first=True)
    
    manager = NotificationManager([notifier1, notifier2])
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)
    
    results = manager.send_all(alert)
    
    assert results == {"TelegramNotifier": True, "LineNotifier": True}
    assert notifier1.attempts == 1
    assert notifier2.attempts == 1

def test_notification_manager_with_retry():
    """Test retry logic for failing notifier"""
    notifier1 = MockNotifier("FailingNotifier", success_on_first=False)
    notifier2 = MockNotifier("SuccessfulNotifier", success_on_first=True)
    
    manager = NotificationManager([notifier1, notifier2], max_retries=2)
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)
    
    results = manager.send_all(alert)
    
    assert results == {"FailingNotifier": True, "SuccessfulNotifier": True}
    assert notifier1.attempts == 2  # Failed first, succeeded on retry
    assert notifier2.attempts == 1

def test_notification_manager_all_fail():
    """Test all notifiers failing"""
    notifier1 = MockNotifier("AlwaysFails", success_on_first=False)
    
    manager = NotificationManager([notifier1], max_retries=1)
    alert = Alert("test", "2024-01-01 12:00", 25.0, 121.5)
    
    results = manager.send_all(alert)
    
    assert results == {"AlwaysFails": False}
    assert notifier1.attempts == 2  # Initial + 1 retry

def test_send_message_all():
    """Test sending messages to all notifiers"""
    notifier1 = MockNotifier("Notifier1", success_on_first=True)
    notifier2 = MockNotifier("Notifier2", success_on_first=True)
    
    manager = NotificationManager([notifier1, notifier2])
    results = manager.send_message_all("test message")
    
    assert results == {"Notifier1": True, "Notifier2": True}

def test_get_notifier_status():
    """Test getting notifier status"""
    notifier1 = MockNotifier("TelegramNotifier")
    notifier2 = MockNotifier("LineNotifier")
    
    manager = NotificationManager([notifier1, notifier2])
    status = manager.get_notifier_status()
    
    assert status == {"TelegramNotifier": "enabled", "LineNotifier": "enabled"}
```

- [ ] **Step 3: Run NotificationManager tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_notification_manager.py -v
```
Expected: 5 tests PASS

- [ ] **Step 4: Commit**

```bash
git add infrastructure/notification_manager.py tests/unit/test_notification_manager.py
git commit -m "feat: add NotificationManager for multi-channel support"
```

### Task 7: Update configuration

**Files:**
- Modify: `config.yaml`
- Modify: `infrastructure/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Update config.yaml with Line and Imgur settings**

```yaml
# config.yaml
PROD:
  DEBUG: False
  # Existing Telegram config
  TELEGRAM_TOKEN: "..."
  TELEGRAM_CHAT_ID: "..."
  # New Line config
  LINE_CHANNEL_ACCESS_TOKEN: "..."
  LINE_CHANNEL_SECRET: "..."
  LINE_USER_ID: "..."  # Line User ID or Group ID
  # New Imgur config (optional)
  IMGUR_CLIENT_ID: "..."
  # Existing CWA config
  CWB_TOKEN: "..."
  LOG: ./log/thunder.log
  AREAS:
    - [22.65694, 22.598, 120.158, 120.3025]
    - [22.58, 22.52, 120.177, 120.349]
    - [23, 22, 120, 130]

STAGE:
  DEBUG: True
  # Existing Telegram config
  TELEGRAM_TOKEN: "..."
  TELEGRAM_CHAT_ID: "..."
  # New Line config
  LINE_CHANNEL_ACCESS_TOKEN: "..."
  LINE_CHANNEL_SECRET: "..."
  LINE_USER_ID: "..."  # Line User ID or Group ID
  # New Imgur config (optional)
  IMGUR_CLIENT_ID: "..."
  # Existing CWA config
  CWB_TOKEN: "..."
  LOG: ./log/thunder_stage.log
  AREAS:
    - [23.76, 23.73, 120.58, 120.65]
```

- [ ] **Step 2: Update config.py with validation**

```python
# infrastructure/config.py
from typing import Dict, Any
import yaml
import logging

logger = logging.getLogger(__name__)

def load_config(env: str = "PROD") -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    
    Args:
        env: Environment name (PROD or STAGE)
        
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        ValueError: If config file missing or required configs missing
        FileNotFoundError: If config.yaml not found
    """
    try:
        with open("config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config.yaml not found")
        raise
    
    if env not in config:
        raise ValueError(f"Environment '{env}' not found in config.yaml")
    
    env_config = config.get(env, {})
    
    # Validate required configuration
    required_keys = [
        "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID",
        "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET", "LINE_USER_ID",
        "CWB_TOKEN", "LOG", "AREAS"
    ]
    
    missing_keys = [key for key in required_keys if key not in env_config]
    if missing_keys:
        raise ValueError(f"Missing required config in {env}: {', '.join(missing_keys)}")
    
    # Validate AREAS format
    areas = env_config.get("AREAS", [])
    if not isinstance(areas, list):
        raise ValueError("AREAS must be a list")
    for area in areas:
        if not isinstance(area, list) or len(area) != 4:
            raise ValueError(f"Invalid AREA format: {area}. Expected [top, down, left, right]")
    
    logger.info(f"Configuration loaded for environment: {env}")
    return env_config
```

- [ ] **Step 3: Write config tests**

```python
# tests/unit/test_config.py
import pytest
import tempfile
import yaml
from pathlib import Path
from infrastructure.config import load_config

def test_load_config_success():
    """Test successful configuration loading"""
    config_data = {
        "PROD": {
            "TELEGRAM_TOKEN": "telegram_token",
            "TELEGRAM_CHAT_ID": "chat_id",
            "LINE_CHANNEL_ACCESS_TOKEN": "line_token",
            "LINE_CHANNEL_SECRET": "line_secret",
            "LINE_USER_ID": "user123",
            "CWB_TOKEN": "cwb_token",
            "LOG": "./log/thunder.log",
            "AREAS": [[22.0, 21.0, 120.0, 121.0]]
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name
    
    try:
        # Temporarily replace config.yaml
        original_config = Path("config.yaml")
        backup = None
        if original_config.exists():
            backup = original_config.read_text()
            original_config.unlink()
        
        Path(config_file).rename("config.yaml")
        
        config = load_config("PROD")
        
        assert config["TELEGRAM_TOKEN"] == "telegram_token"
        assert config["LINE_CHANNEL_ACCESS_TOKEN"] == "line_token"
        assert config["AREAS"] == [[22.0, 21.0, 120.0, 121.0]]
        
    finally:
        # Cleanup
        Path("config.yaml").unlink()
        if backup:
            original_config.write_text(backup)

def test_load_config_missing_env():
    """Test loading missing environment"""
    config_data = {"PROD": {"TEST": "value"}}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name
    
    try:
        original_config = Path("config.yaml")
        backup = None
        if original_config.exists():
            backup = original_config.read_text()
            original_config.unlink()
        
        Path(config_file).rename("config.yaml")
        
        with pytest.raises(ValueError, match="Environment 'STAGE' not found"):
            load_config("STAGE")
            
    finally:
        Path("config.yaml").unlink()
        if backup:
            original_config.write_text(backup)

def test_load_config_missing_required():
    """Test missing required configuration"""
    config_data = {
        "PROD": {
            "TELEGRAM_TOKEN": "token",
            # Missing other required keys
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name
    
    try:
        original_config = Path("config.yaml")
        backup = None
        if original_config.exists():
            backup = original_config.read_text()
            original_config.unlink()
        
        Path(config_file).rename("config.yaml")
        
        with pytest.raises(ValueError, match="Missing required config"):
            load_config("PROD")
            
    finally:
        Path("config.yaml").unlink()
        if backup:
            original_config.write_text(backup)
```

- [ ] **Step 4: Run config tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_config.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.yaml infrastructure/config.py tests/unit/test_config.py
git commit -m "feat: update config with Line and Imgur support"
```

### Task 8: Refactor AlertService

**Files:**
- Modify: `services/alert_service.py`
- Create: `tests/unit/test_alert_service.py`

- [ ] **Step 1: Refactor AlertService to use NotificationManager**

```python
# services/alert_service.py
from domain.alert_checker import is_alert_valid
from infrastructure import (
    cwb_client,
    image_processor,
    file_repo,
    telegram_notifier,
)
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.notification_manager import NotificationManager
from typing import Any
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.areas = config["AREAS"]
        self.token = config["CWB_TOKEN"]
        
        # Create notifiers
        notifiers = []
        
        # Telegram notifier (always required)
        telegram = telegram_notifier.TelegramNotifier(
            config["TELEGRAM_TOKEN"], 
            config["TELEGRAM_CHAT_ID"]
        )
        notifiers.append(telegram)
        
        # Line notifier (always required, but Imgur optional)
        imgur_client = None
        if "IMGUR_CLIENT_ID" in config and config["IMGUR_CLIENT_ID"]:
            imgur_client = ImgurClient(config["IMGUR_CLIENT_ID"])
        
        line = LineNotifier(
            config["LINE_CHANNEL_ACCESS_TOKEN"], 
            config["LINE_CHANNEL_SECRET"],
            config["LINE_USER_ID"],
            imgur_client=imgur_client
        )
        notifiers.append(line)
        
        # Create notification manager
        self.notification_manager = NotificationManager(notifiers, max_retries=1)
        
        logger.info(f"AlertService initialized with {len(notifiers)} notifiers")
    
    def run(self):
        prev_alerts = file_repo.load_alerts()
        doc = cwb_client.get_thunder_data(self.token)
        current_alerts = is_alert_valid(doc, self.areas)
        
        new_alerts = [a for a in current_alerts if a not in prev_alerts]
        
        if new_alerts:
            # Download and process image once for the batch
            image_processor.download_thunder_img("crop.jpg")
            
            # Send notifications for each new alert
            for alert in new_alerts:
                logger.info(f"Sending alert: {alert}")
                results = self.notification_manager.send_all(alert, "crop.jpg")
                logger.info(f"Notification results: {results}")
            
            # Save current alerts
            file_repo.save_alerts(current_alerts)
            
        elif not current_alerts and prev_alerts:
            # Clear alerts
            file_repo.reset_alerts()
            image_processor.download_thunder_img("crop.jpg")
            
            # Send clearance message
            results = self.notification_manager.send_message_all(
                "⚠️ 雷擊警報解除", 
                "crop.jpg"
            )
            logger.info(f"Clearance notification results: {results}")
        
        else:
            logger.info("No new alerts, no changes")
```

- [ ] **Step 2: Write AlertService tests**

```python
# tests/unit/test_alert_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.alert_service import AlertService
from models.alert import Alert

def create_test_config():
    """Create test configuration"""
    return {
        "AREAS": [[25.0, 24.0, 121.0, 122.0]],
        "CWB_TOKEN": "cwb_test_token",
        "TELEGRAM_TOKEN": "telegram_test_token",
        "TELEGRAM_CHAT_ID": "telegram_chat_id",
        "LINE_CHANNEL_ACCESS_TOKEN": "line_access_token",
        "LINE_CHANNEL_SECRET": "line_secret",
        "LINE_USER_ID": "line_user_id",
        "IMGUR_CLIENT_ID": "imgur_client_id",
        "LOG": "./log/test.log"
    }

def test_alert_service_initialization():
    """Test AlertService initializes correctly"""
    config = create_test_config()
    
    with patch('services.alert_service.TelegramNotifier') as mock_telegram, \
         patch('services.alert_service.LineNotifier') as mock_line, \
         patch('services.alert_service.ImgurClient') as mock_imgur, \
         patch('services.alert_service.NotificationManager') as mock_manager:
        
        mock_telegram_instance = Mock()
        mock_telegram.return_value = mock_telegram_instance
        
        mock_line_instance = Mock()
        mock_line.return_value = mock_line_instance
        
        mock_imgur_instance = Mock()
        mock_imgur.return_value = mock_imgur_instance
        
        mock_manager_instance = Mock()
        mock_manager.return_value = mock_manager_instance
        
        service = AlertService(config)
        
        # Verify notifiers created
        mock_telegram.assert_called_once_with("telegram_test_token", "telegram_chat_id")
        mock_imgur.assert_called_once_with("imgur_client_id")
        mock_line.assert_called_once_with(
            "line_access_token", "line_secret", "line_user_id", 
            imgur_client=mock_imgur_instance
        )
        
        # Verify notification manager created with both notifiers
        mock_manager.assert_called_once()
        call_args = mock_manager.call_args[0]
        assert len(call_args[0]) == 2  # Two notifiers
        assert call_args[0][0] == mock_telegram_instance
        assert call_args[0][1] == mock_line_instance
        assert call_args[1] == {'max_retries': 1}

def test_run_with_new_alerts():
    """Test run() with new alerts"""
    config = create_test_config()
    sample_alerts = [
        Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5),
        Alert("Cloud-to-cloud", "2024-01-01 12:05", 25.1, 121.6)
    ]
    
    with patch('services.alert_service.file_repo.load_alerts') as mock_load, \
         patch('services.alert_service.cwb_client.get_thunder_data') as mock_cwb, \
         patch('services.alert_service.is_alert_valid') as mock_checker, \
         patch('services.alert_service.image_processor.download_thunder_img') as mock_download, \
         patch('services.alert_service.file_repo.save_alerts') as mock_save, \
         patch('services.alert_service.NotificationManager') as mock_manager_class:
        
        # Setup mocks
        mock_load.return_value = []  # No previous alerts
        mock_doc = Mock()
        mock_cwb.return_value = mock_doc
        mock_checker.return_value = sample_alerts  # Current alerts
        
        mock_manager = Mock()
        mock_manager.send_all.return_value = {"TelegramNotifier": True, "LineNotifier": True}
        mock_manager_class.return_value = mock_manager
        
        # Create and run service
        service = AlertService(config)
        service.run()
        
        # Verify behavior
        mock_load.assert_called_once()
        mock_cwb.assert_called_once_with("cwb_test_token")
        mock_checker.assert_called_once_with(mock_doc, config["AREAS"])
        mock_download.assert_called_once_with("crop.jpg")
        
        # Should send notifications for each new alert
        assert mock_manager.send_all.call_count == 2
        mock_save.assert_called_once_with(sample_alerts)

def test_run_with_clearance():
    """Test run() when alerts clear"""
    config = create_test_config()
    previous_alerts = [Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5)]
    
    with patch('services.alert_service.file_repo.load_alerts') as mock_load, \
         patch('services.alert_service.cwb_client.get_thunder_data') as mock_cwb, \
         patch('services.alert_service.is_alert_valid') as mock_checker, \
         patch('services.alert_service.image_processor.download_thunder_img') as mock_download, \
         patch('services.alert_service.file_repo.reset_alerts') as mock_reset, \
         patch('services.alert_service.NotificationManager') as mock_manager_class:
        
        # Setup mocks: previous alerts exist, but no current alerts
        mock_load.return_value = previous_alerts
        mock_doc = Mock()
        mock_cwb.return_value = mock_doc
        mock_checker.return_value = []  # No current alerts
        
        mock_manager = Mock()
        mock_manager.send_message_all.return_value = {"TelegramNotifier": True, "LineNotifier": True}
        mock_manager_class.return_value = mock_manager
        
        # Create and run service
        service = AlertService(config)
        service.run()
        
        # Verify clearance behavior
        mock_reset.assert_called_once()
        mock_download.assert_called_once_with("crop.jpg")
        mock_manager.send_message_all.assert_called_once_with("⚠️ 雷擊警報解除", "crop.jpg")
```

- [ ] **Step 3: Run AlertService tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/test_alert_service.py -v
```
Expected: 3 tests PASS

- [ ] **Step 4: Commit**

```bash
git add services/alert_service.py tests/unit/test_alert_service.py
git commit -m "refactor: AlertService uses NotificationManager"
```

### Task 9: Integration tests and final verification

**Files:**
- Create: `tests/integration/test_notification_flow.py`
- Modify: `app/main.py` (minor logging update)

- [ ] **Step 1: Create integration test**

```python
# tests/integration/test_notification_flow.py
"""
Integration tests for the complete notification flow.
These tests verify components work together correctly.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.alert_service import AlertService
from infrastructure.notification_manager import NotificationManager
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from models.alert import Alert

def create_integration_config():
    """Create configuration for integration tests"""
    return {
        "AREAS": [[25.0, 24.0, 121.0, 122.0]],
        "CWB_TOKEN": "test_cwb_token",
        "TELEGRAM_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "test_chat_id",
        "LINE_CHANNEL_ACCESS_TOKEN": "test_line_token",
        "LINE_CHANNEL_SECRET": "test_line_secret",
        "LINE_USER_ID": "test_line_user",
        "IMGUR_CLIENT_ID": "test_imgur_id",
        "LOG": "./log/test_integration.log"
    }

def test_notification_manager_integration():
    """Test NotificationManager integrates with real notifiers"""
    config = create_integration_config()
    
    # Create real notifier instances with mocked APIs
    with patch('infrastructure.telegram_notifier.requests.post') as mock_telegram_api, \
         patch('infrastructure.line_notifier.requests.post') as mock_line_api, \
         patch('infrastructure.imgur_client.requests.post') as mock_imgur_api:
        
        # Setup API mocks
        telegram_response = Mock()
        telegram_response.raise_for_status.return_value = None
        mock_telegram_api.return_value = telegram_response
        
        line_response = Mock()
        line_response.raise_for_status.return_value = None
        mock_line_api.return_value = line_response
        
        imgur_response = Mock()
        imgur_response.json.return_value = {
            "success": True,
            "data": {"link": "https://i.imgur.com/test.jpg"}
        }
        imgur_response.raise_for_status.return_value = None
        mock_imgur_api.return_value = imgur_response
        
        # Create real components
        imgur_client = ImgurClient(config["IMGUR_CLIENT_ID"])
        telegram_notifier = TelegramNotifier(config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"])
        line_notifier = LineNotifier(
            config["LINE_CHANNEL_ACCESS_TOKEN"],
            config["LINE_CHANNEL_SECRET"],
            config["LINE_USER_ID"],
            imgur_client=imgur_client
        )
        
        # Create notification manager
        manager = NotificationManager([telegram_notifier, line_notifier])
        
        # Test sending alert
        alert = Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5)
        results = manager.send_all(alert, "test_image.jpg")
        
        # Verify both notifiers were called
        assert results["TelegramNotifier"] is True
        assert results["LineNotifier"] is True
        
        # Verify API calls
        assert mock_telegram_api.call_count >= 1  # At least one message
        assert mock_line_api.call_count == 1
        assert mock_imgur_api.call_count == 1

def test_alert_service_integration():
    """Test AlertService integration with all components"""
    config = create_integration_config()
    
    # Mock all external dependencies
    with patch('services.alert_service.file_repo.load_alerts') as mock_load, \
         patch('services.alert_service.cwb_client.get_thunder_data') as mock_cwb, \
         patch('services.alert_service.is_alert_valid') as mock_checker, \
         patch('services.alert_service.image_processor.download_thunder_img') as mock_download, \
         patch('services.alert_service.file_repo.save_alerts') as mock_save, \
         patch('services.alert_service.TelegramNotifier') as mock_telegram_class, \
         patch('services.alert_service.LineNotifier') as mock_line_class, \
         patch('services.alert_service.ImgurClient') as mock_imgur_class, \
         patch('services.alert_service.NotificationManager') as mock_manager_class:
        
        # Setup test data
        test_alerts = [Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5)]
        mock_load.return_value = []
        mock_doc = Mock()
        mock_cwb.return_value = mock_doc
        mock_checker.return_value = test_alerts
        
        # Setup component mocks
        mock_telegram = Mock()
        mock_telegram_class.return_value = mock_telegram
        
        mock_imgur = Mock()
        mock_imgur_class.return_value = mock_imgur
        
        mock_line = Mock()
        mock_line_class.return_value = mock_line
        
        mock_manager = Mock()
        mock_manager.send_all.return_value = {"TelegramNotifier": True, "LineNotifier": True}
        mock_manager_class.return_value = mock_manager
        
        # Run the service
        service = AlertService(config)
        service.run()
        
        # Verify component interactions
        mock_telegram_class.assert_called_once_with(config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"])
        mock_imgur_class.assert_called_once_with(config["IMGUR_CLIENT_ID"])
        mock_line_class.assert_called_once_with(
            config["LINE_CHANNEL_ACCESS_TOKEN"],
            config["LINE_CHANNEL_SECRET"],
            config["LINE_USER_ID"],
            imgur_client=mock_imgur
        )
        mock_manager_class.assert_called_once_with([mock_telegram, mock_line], max_retries=1)
        
        # Verify service logic
        mock_download.assert_called_once_with("crop.jpg")
        mock_manager.send_all.assert_called_once_with(test_alerts[0], "crop.jpg")
        mock_save.assert_called_once_with(test_alerts)
```

- [ ] **Step 2: Update main.py logging**

```python
# app/main.py (add import and update logging)
from services.alert_service import AlertService
from infrastructure.config import load_config
from loguru import logger
import argparse
import sys

def main() -> None:
    try:
        config = load_config(env=parse_args())
        logger.add(config["LOG"], rotation="1 week")
        logger.info(f"Starting Thunder Alert Monitor in {parse_args()} mode")
        service = AlertService(config)
        service.run()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

def parse_args() -> str:
    parser = argparse.ArgumentParser(description="Thunder Monitor")
    parser.add_argument("--env", default="PROD", choices=["PROD", "STAGE"], help="Environment config")
    args = parser.parse_args()
    return args.env

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run integration tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/integration/test_notification_flow.py -v
```
Expected: 2 tests PASS

- [ ] **Step 4: Run all tests**

```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/ -v
```
Expected: All tests PASS (approximately 24-26 tests)

- [ ] **Step 5: Final commit**

```bash
git add tests/integration/test_notification_flow.py app/main.py
git commit -m "feat: add integration tests and update main.py logging"
```

### Task 10: Documentation and cleanup

**Files:**
- Create: `docs/line-notification-setup.md`
- Update: `README.md`

- [ ] **Step 1: Create Line notification setup guide**

```markdown
# Line Notification Setup Guide

## Prerequisites

1. **Line Developer Account**: Register at [Line Developers](https://developers.line.biz/)
2. **Imgur Account**: Register at [Imgur](https://imgur.com/) for image hosting

## Step 1: Create Line Messaging Channel

1. Go to [Line Developers Console](https://developers.line.biz/console/)
2. Click "Create a new provider" (or use existing)
3. Click "Create a new channel" → Select "Messaging API"
4. Fill in channel information:
   - Channel name: "Thunder Alert Monitor"
   - Category: "Weather"
   - Subcategory: "Weather forecast"
5. Complete setup and note:
   - **Channel ID** (not needed for API)
   - **Channel Secret** (save this!)
   - **Channel Access Token** (generate/save this!)

## Step 2: Get Line User/Group ID

### Option A: User ID (personal notifications)
1. Add your Line bot as a friend (scan QR code from console)
2. Send a message to the bot
3. Use webhook or check logs to get your User ID

### Option B: Group ID (group notifications)
1. Create a group in Line
2. Add your bot to the group
3. Send a message in the group
4. Check webhook logs for Group ID

## Step 3: Get Imgur Client ID

1. Go to [Imgur API Registration](https://api.imgur.com/oauth2/addclient)
2. Register new application:
   - Application name: "Thunder Alert Monitor"
   - Authorization type: "OAuth 2 authorization without a callback URL"
3. Note your **Client ID**

## Step 4: Update Configuration

Edit `config.yaml`:

```yaml
PROD:
  # ... existing config ...
  LINE_CHANNEL_ACCESS_TOKEN: "your_channel_access_token_here"
  LINE_CHANNEL_SECRET: "your_channel_secret_here"
  LINE_USER_ID: "your_user_or_group_id_here"
  IMGUR_CLIENT_ID: "your_imgur_client_id_here"  # Optional
```

## Step 5: Install New Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `line-bot-sdk` - Line Messaging API
- `pyimgur` - Imgur API (optional, for images in Line)
- `pytest` - Testing framework

## Step 6: Test the System

1. Run tests:
   ```bash
   python -m pytest tests/ -v
   ```

2. Run in staging mode:
   ```bash
   python app/main.py --env=STAGE
   ```

## Troubleshooting

### Line API Errors
- **401 Unauthorized**: Check Channel Access Token
- **400 Bad Request**: Verify User/Group ID format
- **429 Too Many Requests**: Rate limit reached (1000 messages/month free tier)

### Imgur Issues
- **403 Forbidden**: Check Client ID
- **Rate limiting**: Free tier allows 1250 uploads/day
- Images are publicly accessible by default

### No Images in Line
- Imgur Client ID not configured
- Image upload failed (check logs)
- Line only shows first image in multi-image messages

## Monitoring

Check log files for notification status:
- `./log/thunder.log` (PROD)
- `./log/thunder_stage.log` (STAGE)

Each notification attempt logs:
- Success/failure per channel
- Retry attempts
- Error details if failed
```

- [ ] **Step 2: Update README.md**

Add to the README.md Features section:
```markdown
- Dual notifications: Telegram + Line Messaging API
- Imgur integration for Line image support
- Configurable notification channels
- Improved error handling with retry logic
- Comprehensive test coverage
```

- [ ] **Step 3: Run final verification**

```bash
cd /Users/sychen/thunder-monitor
# Check all imports work
python -c "from infrastructure.notifier import Notifier; print('Notifier import OK')"
python -c "from infrastructure.line_notifier import LineNotifier; print('LineNotifier import OK')"
python -c "from infrastructure.notification_manager import NotificationManager; print('NotificationManager import OK')"

# Check config validation
python -c "from infrastructure.config import load_config; print('Config import OK')"
```

- [ ] **Step 4: Final commit**

```bash
git add docs/line-notification-setup.md README.md
git commit -m "docs: add Line notification setup guide and update README"
```

## Verification

### End-to-End Test Commands

1. **Run all unit tests:**
```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/unit/ -v
```

2. **Run integration tests:**
```bash
cd /Users/sychen/thunder-monitor
python -m pytest tests/integration/ -v
```

3. **Test configuration loading:**
```bash
cd /Users/sychen/thunder-monitor
python -c "
from infrastructure.config import load_config
try:
    config = load_config('PROD')
    print('✓ Config validation works')
    print(f'✓ Found {len(config.get(\"AREAS\", []))} areas')
except Exception as e:
    print(f'✗ Config error: {e}')
"
```

4. **Test notification components:**
```bash
cd /Users/sychen/thunder-monitor
python -c "
from infrastructure.notifier import Notifier
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.line_notifier import LineNotifier
from infrastructure.notification_manager import NotificationManager

print('✓ All imports successful')
print('✓ Notifier interface defined')
print('✓ TelegramNotifier implements Notifier:', issubclass(TelegramNotifier, Notifier))
print('✓ LineNotifier implements Notifier:', issubclass(LineNotifier, Notifier))
"
```

### Expected Final Structure
```
thunder-monitor/
├── infrastructure/
│   ├── notifier.py              # Abstract interface
│   ├── telegram_notifier.py     # Updated Telegram implementation
│   ├── line_notifier.py         # New Line implementation
│   ├── imgur_client.py          # New Imgur client
│   ├── notification_manager.py  # New multi-channel manager
│   ├── config.py                # Updated with validation
│   └── ... (existing files)
├── services/
│   └── alert_service.py         # Refactored to use NotificationManager
├── tests/
│   ├── unit/                    # Unit tests for all components
│   ├── integration/             # Integration tests
│   └── conftest.py              # Test fixtures
├── docs/
│   └── line-notification-setup.md # Setup guide
└── config.yaml                  # Updated with Line/Imgur configs
```

### Success Criteria Check
- [ ] All tests pass
- [ ] Configuration validates Line/Imgur credentials
- [ ] AlertService uses NotificationManager
- [ ] Both Telegram and Line notifiers work
- [ ] Imgur integration optional (works without it)
- [ ] Error handling with retry logic implemented
- [ ] Backward compatibility maintained
- [ ] Documentation updated