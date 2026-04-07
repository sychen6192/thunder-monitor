import pytest
from datetime import datetime
from models.alert import Alert


@pytest.fixture
def sample_alerts():
    """Return a list of sample Alert objects for testing."""
    return [
        Alert(
            category="Thunderstorm",
            occur_time=datetime.now().isoformat(),
            latitude=25.0330,
            longitude=121.5654
        ),
        Alert(
            category="Heavy Rain",
            occur_time=datetime.now().isoformat(),
            latitude=24.1477,
            longitude=120.6736
        ),
        Alert(
            category="Flood",
            occur_time=datetime.now().isoformat(),
            latitude=22.6273,
            longitude=120.3014
        )
    ]


@pytest.fixture
def single_alert():
    """Return a single Alert object for testing."""
    return Alert(
        category="Test Alert",
        occur_time="2024-01-01T12:00:00",
        latitude=0.0,
        longitude=0.0
    )


@pytest.fixture
def empty_alerts():
    """Return an empty list of alerts."""
    return []