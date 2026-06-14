from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Alert:
    """Represents a weather alert with location and timing information.

    Attributes:
        category: Type of alert (e.g., "Cloud-to-ground", "Cloud-to-cloud")
        occur_time: Time when the alert occurred (format: "YYYY-MM-DD HH:MM")
        latitude: Geographic latitude in decimal degrees
        longitude: Geographic longitude in decimal degrees

    Serialization:
        This class can be serialized to/from dictionaries for storage.
        Use `to_dict()` for serialization and the constructor for deserialization.
    """

    category: str
    occur_time: str
    latitude: float
    longitude: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Alert instance to a dictionary for serialization.

        Returns:
            Dictionary containing all alert attributes suitable for JSON serialization.
        """
        return {
            "category": self.category,
            "occur_time": self.occur_time,
            "latitude": self.latitude,
            "longitude": self.longitude
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create an Alert instance from a dictionary.

        Args:
            data: Dictionary containing alert attributes.

        Returns:
            Alert instance created from the dictionary data.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If data types are invalid.
        """
        return cls(
            category=str(data["category"]),
            occur_time=str(data["occur_time"]),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"])
        )
