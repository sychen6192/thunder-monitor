---
name: Line Notification Integration
description: Design for adding Line Messaging API notifications with Imgur image support
type: feature
---

# Line Notification Integration Design

## Overview
Extend the Thunder Alert Monitor system to send notifications via Line Messaging API in addition to existing Telegram notifications. The solution uses a Strategy Pattern for extensible notification channels and Imgur API for image hosting required by Line.

## Requirements
- Send alerts to both Telegram and Line simultaneously
- Use Line Messaging API (not Line Notify)
- Support images via Imgur API (Line requires HTTPS URLs)
- Improve code organization and testability
- Maintain backward compatibility

## Architecture

### 1. Notification Interface Pattern
```
AlertService → NotificationManager → [Notifier]
                                     ├── TelegramNotifier (updated)
                                     └── LineNotifier (new)
```

### 2. Key Components

#### 2.1 Notifier Interface (`infrastructure/notifier.py`)
```python
from abc import ABC, abstractmethod
from models.alert import Alert

class Notifier(ABC):
    @abstractmethod
    def send(self, alert: Alert, img_path: str | None = None) -> bool:
        """Send alert notification, return success status"""
        pass
    
    @abstractmethod  
    def send_message(self, message: str, img_path: str | None = None) -> bool:
        """Send simple message, return success status"""
        pass
```

#### 2.2 LineNotifier (`infrastructure/line_notifier.py`)
- Implements `Notifier` interface
- Uses Line Messaging API v2
- Integrates with ImgurClient for image hosting
- Error handling with retry support
- Text fallback if image upload fails

#### 2.3 ImgurClient (`infrastructure/imgur_client.py`)
- Uploads images to Imgur via API
- Returns HTTPS URLs for Line messages
- Optional cleanup (image deletion)
- Graceful failure handling

#### 2.4 NotificationManager (`infrastructure/notification_manager.py`)
- Manages multiple notifiers
- Retry logic (configurable attempts)
- Independent failure handling (one notifier failing doesn't stop others)
- Returns success/failure status per notifier

#### 2.5 Updated TelegramNotifier (`infrastructure/telegram_notifier.py`)
- Updated to implement `Notifier` interface
- Maintains existing functionality

### 3. Configuration Updates

#### 3.1 config.yaml Additions
```yaml
PROD:
  # Existing
  TELEGRAM_TOKEN: "..."
  TELEGRAM_CHAT_ID: "..."
  CWB_TOKEN: "..."
  LOG: ./log/thunder.log
  AREAS: [...]
  
  # New Line configuration
  LINE_CHANNEL_ACCESS_TOKEN: "..."
  LINE_CHANNEL_SECRET: "..."
  LINE_USER_ID: "..."  # Line User ID or Group ID
  
  # New Imgur configuration (optional)
  IMGUR_CLIENT_ID: "..."
```

#### 3.2 Configuration Validation (`infrastructure/config.py`)
- Validates all required credentials
- Imgur client ID is optional (images skipped if not provided)
- Environment-specific configuration preserved

### 4. Data Flow

#### 4.1 Alert Processing
```
1. AlertService detects new alerts
2. Creates NotificationManager with configured notifiers
3. NotificationManager.send_all() called with alert and image
4. Each notifier processes independently:
   - TelegramNotifier: sends via Telegram API
   - LineNotifier: 
     a. Uploads image to Imgur (if client available)
     b. Sends text + image URL via Line API
5. Results aggregated and logged
```

#### 4.2 Image Handling Flow for Line
```
1. LineNotifier receives image path
2. If ImgurClient configured:
   a. Upload image to Imgur (base64 encoded)
   b. Receive HTTPS URL
   c. Include image message in Line payload
3. If ImgurClient not configured or upload fails:
   a. Send text-only message
   b. Log warning
4. Text message always sent regardless of image status
```

### 5. Error Handling

#### 5.1 Failure Modes
- **Line API failure**: Retry up to configured limit, log error, continue with other notifiers
- **Imgur upload failure**: Send text-only to Line, log warning
- **Configuration missing**: Skip affected notifier, log error during initialization
- **Network issues**: Retry logic in NotificationManager

#### 5.2 Retry Strategy
- Configurable max retries per notifier (default: 1)
- Exponential backoff optional (future enhancement)
- Independent retry per notifier

### 6. Testing Strategy

#### 6.1 Unit Tests
- `Notifier` interface validation
- `LineNotifier` with mocked Line API
- `ImgurClient` with mocked Imgur API
- `NotificationManager` with mocked notifiers
- `TelegramNotifier` updates

#### 6.2 Integration Tests
- End-to-end alert flow (optional)
- API integration tests (sandbox environment)
- Configuration validation tests

#### 6.3 Test Fixtures
- Mock Line API responses
- Mock Imgur upload responses
- Sample alert data
- Test configuration

### 7. Security Considerations

#### 7.1 Credential Management
- Configuration stored in config.yaml (existing pattern)
- No credentials in code
- Environment-specific configuration maintained

#### 7.2 API Security
- Line Channel Access Token protected
- Imgur Client ID (public, but rate-limited)
- HTTPS for all API calls

#### 7.3 Image Privacy
- Imgur images may be publicly accessible
- Consider Imgur album privacy settings for sensitive images
- Optional image deletion after sending (future enhancement)

### 8. Performance Considerations

#### 8.1 API Rate Limits
- Line Messaging API: 1000 messages/month (free tier)
- Imgur API: 1250 uploads/day (free tier)
- Telegram API: ~30 messages/second

#### 8.2 Parallel Processing
- Notifiers run sequentially (simple implementation)
- Future: async/parallel execution for better performance
- Current volume doesn't require parallel processing

#### 8.3 Image Processing
- Local image processing unchanged
- Additional Imgur upload adds latency (~1-2 seconds)
- Upload happens once per alert batch (not per notifier)

### 9. Deployment Plan

#### Phase 1: Preparation
1. Register Line Developer account, create Messaging Channel
2. Obtain Line Channel Access Token and Channel Secret
3. Register Imgur application, get Client ID
4. Update configuration with new credentials

#### Phase 2: Implementation
1. Create Notifier interface and update TelegramNotifier
2. Implement ImgurClient
3. Implement LineNotifier
4. Create NotificationManager
5. Refactor AlertService
6. Add unit tests

#### Phase 3: Testing
1. Run existing test suite
2. Test new components with mocked APIs
3. Optional: Integration test in sandbox
4. Configuration validation

#### Phase 4: Deployment
1. Update config.yaml with new credentials
2. Deploy updated code
3. Monitor logs for both Telegram and Line notifications
4. Verify alert delivery to both channels

### 10. Future Enhancements

#### 10.1 Additional Notification Channels
- Email notifications
- SMS notifications
- Discord/ Slack webhooks
- Push notifications

#### 10.2 Advanced Features
- Notification templates (customizable per channel)
- Priority-based delivery
- Delivery receipts and analytics
- User preference management

#### 10.3 Performance Improvements
- Async/parallel notifier execution
- Image caching and reuse
- Batch notification delivery

#### 10.4 Monitoring
- Delivery success/failure metrics
- API usage tracking
- Alert volume analytics

## Success Criteria
1. Alerts delivered to both Telegram and Line simultaneously
2. Images visible in Line messages (when Imgur configured)
3. Error handling prevents single failure from blocking system
4. Code organization improved (Strategy Pattern)
5. Test coverage maintained or improved
6. Backward compatibility preserved

## Dependencies
1. Line Messaging API access
2. Imgur API Client ID (optional, for images)
3. Existing Telegram bot configuration
4. Python 3.11+ with required packages

## Risks and Mitigations
1. **Line API changes**: Follow Line API documentation, version pinning
2. **Imgur rate limits**: Monitor usage, implement exponential backoff
3. **Credential leakage**: Store in config.yaml only, no hardcoded values
4. **Service downtime**: Independent notifier failure handling