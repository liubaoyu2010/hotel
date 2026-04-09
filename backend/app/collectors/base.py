from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawActivity:
    """Standardized activity data produced by collectors."""

    title: str
    description: str | None = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = field(default_factory=datetime.utcnow)
    address: str | None = None
    source: str = ""
    source_id: str = ""
    source_url: str | None = None
    activity_type: str = "other"
    latitude: float | None = None
    longitude: float | None = None
    estimated_attendees: int | None = None


class BaseCollector(ABC):
    """Abstract base class for activity collectors."""

    name: str = "base"
    display_name: str = "Base Collector"
    priority: int = 50
    enabled_by_default: bool = True

    @abstractmethod
    def collect(self, city: str, radius_km: float = 3.0) -> list[RawActivity]:
        """Execute collection and return raw activity list."""
        ...
