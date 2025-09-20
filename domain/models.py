from dataclasses import dataclass

@dataclass
class Alert:
    category: str
    occur_time: str
    latitude: float
    longitude: float
