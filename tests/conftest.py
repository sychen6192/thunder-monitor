import pytest
from models.alert import Alert


@pytest.fixture
def sample_alert():
    """Fixture that returns a single Alert object for testing.

    Returns:
        Alert: A sample Alert object with category "Cloud-to-ground",
               occur_time "2024-01-01 12:00", latitude 25.0, longitude 121.5.
    """
    return Alert(
        category="Cloud-to-ground",
        occur_time="2024-01-01 12:00",
        latitude=25.0,
        longitude=121.5
    )


@pytest.fixture
def sample_alerts():
    """Fixture that returns a list of two Alert objects for testing.

    Returns:
        List[Alert]: A list containing two sample Alert objects:
            - First: Cloud-to-ground at 2024-01-01 12:00, lat 25.0, long 121.5
            - Second: Cloud-to-cloud at 2024-01-01 12:05, lat 25.1, long 121.6
    """
    return [
        Alert("Cloud-to-ground", "2024-01-01 12:00", 25.0, 121.5),
        Alert("Cloud-to-cloud", "2024-01-01 12:05", 25.1, 121.6)
    ]