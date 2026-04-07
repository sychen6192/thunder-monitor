import pytest
from models.alert import Alert


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