"""Data models for schedule events."""

from dataclasses import dataclass, field
from datetime import time


@dataclass
class ScheduleEvent:
    """Represents a single scheduled class/event."""
    
    course_name: str
    event_type: str
    instructor: str
    room: str
    weekday: int  # 0-4: Monday-Friday
    start_time: time
    end_time: time
    repeat_interval: int = field(default=1)  # 1 = weekly, 2 = biweekly, etc.
    event_type_code: str = field(default="")  # W, L, P, S, C
    
    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 4:
            raise ValueError(f"Weekday must be 0-4 (Mon-Fri), got {self.weekday}")
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")
        if self.repeat_interval < 1:
            raise ValueError("Repeat interval must be at least 1")
