"""File-based repository for storing and retrieving Alert objects.

This module provides functions to save, load, and reset alerts using
a simple JSONL (JSON Lines) file format. Each alert is stored as a
separate JSON object on its own line.

Note: The file path is currently hardcoded as 'alert.txt' in the
current working directory. In a production environment, this should
be made configurable via environment variables or a configuration file.
"""

import json
import logging
from pathlib import Path
from typing import List

from models.alert import Alert


# Hardcoded file path - consider making this configurable in production
ALERT_FILE = Path("alert.txt")

logger = logging.getLogger(__name__)


def save_alerts(alerts: List[Alert]) -> None:
    """Save a list of Alert objects to the file.

    Args:
        alerts: List of Alert objects to save.

    Raises:
        PermissionError: If the file cannot be written due to permission issues.
        OSError: For other file system errors (disk full, etc.).
        TypeError: If alerts cannot be serialized to JSON.
    """
    if not alerts:
        # Handle empty list by clearing the file
        reset_alerts()
        return

    try:
        with open(ALERT_FILE, "w", encoding="utf-8") as f:
            for alert in alerts:
                # Use the Alert class's to_dict() method for serialization
                alert_data = alert.to_dict()
                f.write(json.dumps(alert_data) + "\n")
        logger.debug(f"Successfully saved {len(alerts)} alerts to {ALERT_FILE}")
    except PermissionError:
        logger.error(f"Permission denied when trying to write to {ALERT_FILE}")
        raise
    except OSError as e:
        logger.error(f"OS error when saving alerts to {ALERT_FILE}: {e}")
        raise
    except (TypeError, ValueError) as e:
        logger.error(f"Serialization error when saving alerts: {e}")
        raise


def load_alerts() -> List[Alert]:
    """Load Alert objects from the file.

    Returns:
        List of Alert objects loaded from the file.

    Raises:
        PermissionError: If the file cannot be read due to permission issues.
        json.JSONDecodeError: If the file contains invalid JSON.
        OSError: For other file system errors.
    """
    if not ALERT_FILE.exists():
        logger.debug(f"Alert file {ALERT_FILE} does not exist, returning empty list")
        return []

    try:
        alerts = []
        with open(ALERT_FILE, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue  # Skip empty lines

                try:
                    alert_data = json.loads(line)

                    # Create Alert object using from_dict() method
                    try:
                        alert = Alert.from_dict(alert_data)
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Line {line_num}: Invalid alert data - {e}")
                        continue
                    alerts.append(alert)

                except json.JSONDecodeError as e:
                    logger.warning(f"Line {line_num}: Invalid JSON - {e}")
                    continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Line {line_num}: Invalid data type - {e}")
                    continue

        logger.debug(f"Successfully loaded {len(alerts)} alerts from {ALERT_FILE}")
        return alerts

    except PermissionError:
        logger.error(f"Permission denied when trying to read from {ALERT_FILE}")
        raise
    except OSError as e:
        logger.error(f"OS error when loading alerts from {ALERT_FILE}: {e}")
        raise


def reset_alerts() -> None:
    """Clear all alerts from the file.

    Raises:
        PermissionError: If the file cannot be written due to permission issues.
        OSError: For other file system errors.
    """
    try:
        ALERT_FILE.write_text("")
        logger.debug(f"Successfully reset alert file {ALERT_FILE}")
    except PermissionError:
        logger.error(f"Permission denied when trying to reset {ALERT_FILE}")
        raise
    except OSError as e:
        logger.error(f"OS error when resetting alerts file {ALERT_FILE}: {e}")
        raise
