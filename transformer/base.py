"""Abstract base class for schedule transformers."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from scraper.models import ScheduleEvent


class BaseTransformer(ABC):
    """Abstract base class defining the interface for schedule transformers.
    
    Extend this class to implement transformers for different output formats
    (e.g., iCalendar, Google Calendar API, JSON, etc.).
    """
    
    @abstractmethod
    def transform(
        self,
        events: list[ScheduleEvent],
        start_date: date,
        end_date: date
    ) -> Any:
        """Transform schedule events into the target format.
        
        Args:
            events: List of schedule events to transform.
            start_date: First day of the schedule period.
            end_date: Last day of the schedule period.
            
        Returns:
            Transformed data in the target format.
        """
        pass
    
    @abstractmethod
    def save(self, output_path: str) -> None:
        """Save the transformed data to a file.
        
        Args:
            output_path: Path to the output file.
        """
        pass
