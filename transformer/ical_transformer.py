"""iCalendar transformer for schedule events."""

import hashlib
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, vRecur

from scraper.models import ScheduleEvent
from .base import BaseTransformer


class ICalTransformer(BaseTransformer):
    """Transformer that converts schedule events to iCalendar format."""
    
    TIMEZONE = ZoneInfo("Europe/Warsaw")
    ACADEMIC_HOUR_MINUTES = 45
    ACADEMIC_START_OFFSET = 15  # Classes start 15 min after full hour
    
    def __init__(self, apply_academic_hours: bool = False) -> None:
        """Initialize the iCalendar transformer.
        
        Args:
            apply_academic_hours: If True, apply academic hour logic
                (45 min per hour, starts 15 min after full hour).
        """
        self._calendar: Optional[Calendar] = None
        self._apply_academic_hours = apply_academic_hours
    
    def _generate_uid(self, event: ScheduleEvent, start_date: date) -> str:
        """Generate a unique identifier for an event.
        
        Args:
            event: The schedule event.
            start_date: Start date of the schedule period.
            
        Returns:
            Unique identifier string.
        """
        unique_string = (
            f"{event.course_name}-{event.weekday}-"
            f"{event.start_time}-{event.event_type}-{start_date}"
        )
        return hashlib.md5(unique_string.encode()).hexdigest() + "@sis.pg.edu.pl"
    
    def _find_first_occurrence(self, event: ScheduleEvent, start_date: date) -> date:
        """Find the first occurrence of an event on or after start_date.
        
        Args:
            event: The schedule event with weekday information.
            start_date: The earliest possible date.
            
        Returns:
            Date of the first occurrence.
        """
        start_weekday = start_date.weekday()
        target_weekday = event.weekday
        
        days_ahead = target_weekday - start_weekday
        if days_ahead < 0:
            days_ahead += 7
        
        return start_date + timedelta(days=days_ahead)
    
    def transform(
        self,
        events: list[ScheduleEvent],
        start_date: date,
        end_date: date
    ) -> Calendar:
        """Transform schedule events into iCalendar format.
        
        Args:
            events: List of schedule events to transform.
            start_date: First day of the schedule period.
            end_date: Last day of the schedule period.
            
        Returns:
            iCalendar Calendar object.
        """
        self._calendar = Calendar()
        self._calendar.add("prodid", "-//SIS Schedule to iCal//pg-schedule-to-ical//PL")
        self._calendar.add("version", "2.0")
        self._calendar.add("calscale", "GREGORIAN")
        self._calendar.add("method", "PUBLISH")
        self._calendar.add("x-wr-calname", "Schedule")
        self._calendar.add("x-wr-timezone", "Europe/Warsaw")
        
        for schedule_event in events:
            ical_event = Event()
            
            first_date = self._find_first_occurrence(schedule_event, start_date)
            
            if self._apply_academic_hours:
                # Calculate number of academic hours from schedule slots
                start_hour = schedule_event.start_time.hour
                end_hour = schedule_event.end_time.hour
                num_hours = end_hour - start_hour
                
                # Start 15 minutes after the full hour
                academic_start = datetime.combine(
                    first_date,
                    time(start_hour, self.ACADEMIC_START_OFFSET),
                    tzinfo=self.TIMEZONE
                )
                
                # Duration is number of hours * 45 minutes
                duration_minutes = num_hours * self.ACADEMIC_HOUR_MINUTES
                academic_end = academic_start + timedelta(minutes=duration_minutes)
                
                start_datetime = academic_start
                end_datetime = academic_end
            else:
                start_datetime = datetime.combine(
                    first_date,
                    schedule_event.start_time,
                    tzinfo=self.TIMEZONE
                )
                end_datetime = datetime.combine(
                    first_date,
                    schedule_event.end_time,
                    tzinfo=self.TIMEZONE
                )
            
            ical_event.add("uid", self._generate_uid(schedule_event, start_date))
            ical_event.add("dtstart", start_datetime)
            ical_event.add("dtend", end_datetime)
            ical_event.add("dtstamp", datetime.now(self.TIMEZONE))
            
            # Summary format: [W] Course Name
            event_code = schedule_event.event_type_code or ""
            if event_code:
                summary = f"[{event_code}] {schedule_event.course_name}"
            else:
                summary = schedule_event.course_name
            ical_event.add("summary", summary)
            
            if schedule_event.room:
                ical_event.add("location", schedule_event.room)
            
            # Description: just instructor name (no prefix)
            if schedule_event.instructor:
                ical_event.add("description", schedule_event.instructor)
            
            # RRULE UNTIL - use the computed end time for the last occurrence
            until_datetime = datetime.combine(
                end_date,
                end_datetime.time(),
                tzinfo=self.TIMEZONE
            )
            
            rrule = vRecur({
                "freq": "weekly",
                "interval": schedule_event.repeat_interval,
                "until": until_datetime
            })
            ical_event.add("rrule", rrule)
            
            self._calendar.add_component(ical_event)
        
        return self._calendar
    
    def save(self, output_path: str) -> None:
        """Save the calendar to an .ics file.
        
        Args:
            output_path: Path to the output file.
            
        Raises:
            RuntimeError: If transform() hasn't been called yet.
        """
        if self._calendar is None:
            raise RuntimeError("No calendar data. Call transform() first.")
        
        with open(output_path, "wb") as f:
            f.write(self._calendar.to_ical())
